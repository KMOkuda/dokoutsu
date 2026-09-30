"""6a パスワード再発行画面(詳細設計書 docs/design/6a_パスワード再発行画面.md)"""

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from ..forms import PasswordResetConfirmForm, PasswordResetRequestForm
from ..models import EmailSendLog
from ..services import EMAIL_SEND_LIMIT_MESSAGE, reserve_email_send

User = get_user_model()


def password_reset_view(request):
    if request.user.is_authenticated:
        return redirect("active_problems")
    sent_email = request.session.get("password_reset_email")
    resent = request.session.pop("password_reset_resent", False)
    limit_error = None
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        # 登録のないメールアドレスも同じように数え、同じ表示にする(登録の有無を推測させないため)
        if form.is_valid() and not reserve_email_send(
            form.cleaned_data["email"], EmailSendLog.PASSWORD_RESET
        ):
            limit_error = EMAIL_SEND_LIMIT_MESSAGE
        elif form.is_valid():
            email = form.cleaned_data["email"]
            user = User.objects.filter(email=email).first()
            if user is not None:
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                path = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
                link = request.build_absolute_uri(path)
                send_mail(
                    "どこ打つくん パスワード再設定",
                    f"以下のリンクから新しいパスワードを設定してください。\n{link}",
                    None,
                    [email],
                )
            request.session["password_reset_email"] = email
            # 送信完了の画面の「メールを再送する」から送った場合は、再送したことを次の表示で伝える
            # (登録のないメールアドレスでも同じ表示にする)
            request.session["password_reset_resent"] = bool(request.POST.get("resend"))
            return redirect("password_reset")
    else:
        form = PasswordResetRequestForm()
    return render(
        request,
        "accounts/password_reset.html",
        {
            "form": form,
            "sent_email": sent_email,
            "resent": resent,
            "limit_error": limit_error,
            "hide_menu": True,
        },
    )


def password_reset_confirm_view(request, uidb64, token):
    # uidb64はユーザーIDをURLに載せられる形に変換したもの。tokenはDjango標準のパスワード再発行の仕組みで
    # 検証する(有効期限は settings.PASSWORD_RESET_TIMEOUT。パスワードを変更すると使えなくなる)
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and not default_token_generator.check_token(user, token):
        user = None
    if user is None:
        return render(request, "accounts/password_reset_confirm.html", {
            "invalid": True,
            "hide_menu": True,
        })
    success = False
    if request.method == "POST":
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data["new_password"])
            user.save(update_fields=["password"])
            success = True
    else:
        form = PasswordResetConfirmForm()
    return render(
        request,
        "accounts/password_reset_confirm.html",
        {"form": form, "success": success, "hide_menu": True},
    )
