"""3a 新規登録画面(詳細設計書 docs/design/3a_新規登録画面.md)"""

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse

from ..forms import LoginForm, SignupForm
from ..models import EmailSendLog
from ..services import EMAIL_SEND_LIMIT_MESSAGE, reserve_email_send

User = get_user_model()

# 登録確認リンクは、Djangoの署名の仕組み(TimestampSigner)で作る。ユーザーIDに発行時刻と、SECRET_KEYを
# 使った封印を付けたもので、封印が合わない(書き換えられた)ものや期限切れのものは受け付けない。
# パスワード再発行用のトークンは有効期限をサイト全体で1つしか持てない(settings.PASSWORD_RESET_TIMEOUT)ため、
# 有効期限の異なる登録確認には使わない(詳細設計書 3a「7. この画面固有の設計事項」)。
# saltは用途ごとに封印の種類を分けるための文字列で、他の用途で署名した値を登録確認に流用させない。
ACTIVATION_SALT = "dokoutsu.signup.activation"
ACTIVATION_MAX_AGE = 60 * 60 * 24


def _build_activation_link(request, user):
    token = signing.TimestampSigner(salt=ACTIVATION_SALT).sign(str(user.pk))
    path = reverse("activate", kwargs={"token": token})
    return request.build_absolute_uri(path)


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("active_problems")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid() and not reserve_email_send(
            form.cleaned_data["email"], EmailSendLog.SIGNUP
        ):
            # 上限に達している場合は、未確認アカウントの作成・置き換えも行わない
            form.add_error(None, EMAIL_SEND_LIMIT_MESSAGE)
        if form.is_valid():
            user = form.save()
            link = _build_activation_link(request, user)
            send_mail(
                "どこ打つくん 会員登録の確認",
                f"以下のリンクから登録を完了してください。\n{link}",
                None,
                [user.email],
            )
            request.session["signup_email"] = user.email
            return redirect("signup_sent")
    else:
        form = SignupForm()
    return render(request, "accounts/signup.html", {"form": form, "hide_menu": True})


def signup_sent_view(request):
    email = request.session.get("signup_email")
    if not email:
        return redirect("signup")
    limit_error = None
    resent = False
    if request.method == "POST":
        user = User.objects.filter(email=email, is_active=False).first()
        if user and not reserve_email_send(email, EmailSendLog.SIGNUP):
            limit_error = EMAIL_SEND_LIMIT_MESSAGE
        elif user:
            link = _build_activation_link(request, user)
            send_mail(
                "どこ打つくん 会員登録の確認(再送)",
                f"以下のリンクから登録を完了してください。\n{link}",
                None,
                [user.email],
            )
            resent = True
    return render(
        request,
        "accounts/signup_sent.html",
        {"email": email, "limit_error": limit_error, "resent": resent, "hide_menu": True},
    )


def activate_view(request, token):
    try:
        user_pk = signing.TimestampSigner(salt=ACTIVATION_SALT).unsign(
            token, max_age=ACTIVATION_MAX_AGE
        )
        user = User.objects.get(pk=user_pk)
    # 期限切れ(SignatureExpired)は、封印が合わない場合(BadSignature)の一種として扱われる
    except (signing.BadSignature, User.DoesNotExist):
        user = None
    if user is None:
        return render(request, "accounts/login.html", {
            "form": LoginForm(),
            "activation_error": "リンクの有効期限が切れています。お手数ですが、もう一度新規登録を行ってください。",
            "hide_menu": True,
        })
    user.is_active = True
    user.save(update_fields=["is_active"])
    return redirect("login")
