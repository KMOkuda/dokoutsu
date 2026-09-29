from django.contrib.auth import authenticate, get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.http import Http404, HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .forms import (
    AnswerPostForm,
    LoginForm,
    PasswordResetConfirmForm,
    PasswordResetRequestForm,
    ProblemForm,
    SignupForm,
)
from .models import AnswerPost, Problem

User = get_user_model()


def _build_activation_link(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse("activate", kwargs={"uidb64": uidb64, "token": token})
    return request.build_absolute_uri(path)


def _build_reset_link(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
    return request.build_absolute_uri(path)


def _remaining_label(deadline):
    """締切までの残りを「N日」(24時間以上)/「N時間」(24時間未満)で返す。"""
    seconds = (deadline - timezone.now()).total_seconds()
    if seconds <= 0:
        return None
    if seconds >= 24 * 3600:
        return f"{int(seconds // (24 * 3600))}日"
    return f"{max(1, int(seconds // 3600))}時間"


def _answer_url(request, problem):
    return request.build_absolute_uri(reverse("answer_create", kwargs={"pk": problem.pk}))


def _decode_user(uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None
    if not default_token_generator.check_token(user, token):
        return None
    return user


# --- 3a 新規登録画面 ---


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("active_problems")
    if request.method == "POST":
        form = SignupForm(request.POST)
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
    if request.method == "POST":
        user = User.objects.filter(email=email, is_active=False).first()
        if user:
            link = _build_activation_link(request, user)
            send_mail(
                "どこ打つくん 会員登録の確認(再送)",
                f"以下のリンクから登録を完了してください。\n{link}",
                None,
                [user.email],
            )
    return render(
        request, "accounts/signup_sent.html", {"email": email, "hide_menu": True}
    )


def activate_view(request, uidb64, token):
    user = _decode_user(uidb64, token)
    if user is None:
        return render(request, "accounts/login.html", {
            "form": LoginForm(),
            "activation_error": "リンクの有効期限が切れています",
            "hide_menu": True,
        })
    user.is_active = True
    user.save(update_fields=["is_active"])
    return redirect("login")


# --- 3b ログイン画面 ---


def login_view(request):
    if request.user.is_authenticated:
        return redirect("active_problems")
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            login_id = form.cleaned_data["login_id"]
            password = form.cleaned_data["password"]
            user_obj = User.objects.filter(username=login_id).first() or User.objects.filter(
                email=login_id
            ).first()
            error = None
            if user_obj is None:
                error = "IDまたはパスワードが違います"
            elif not user_obj.check_password(password):
                error = "IDまたはパスワードが違います"
            elif not user_obj.is_active:
                error = "メールアドレスの確認が完了していません"
            else:
                user = authenticate(
                    request, username=user_obj.username, password=password
                )
                if user is None:
                    error = "IDまたはパスワードが違います"
                else:
                    auth_login(request, user)
                    if not form.cleaned_data.get("remember"):
                        request.session.set_expiry(0)
                    return redirect("active_problems")
            form.add_error(None, error)
    else:
        form = LoginForm()
    return render(
        request, "accounts/login.html", {"form": form, "hide_menu": True}
    )


def logout_view(request):
    # GETでのログアウトを許すと、外部サイトに置いたリンクや画像で勝手にログアウトさせられるため、POSTに限る
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    auth_logout(request)
    return redirect("login")


# --- 6a パスワード再発行画面 ---


def password_reset_view(request):
    if request.user.is_authenticated:
        return redirect("active_problems")
    sent_email = request.session.get("password_reset_email")
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            user = User.objects.filter(email=email).first()
            if user is not None:
                link = _build_reset_link(request, user)
                send_mail(
                    "どこ打つくん パスワード再設定",
                    f"以下のリンクから新しいパスワードを設定してください。\n{link}",
                    None,
                    [email],
                )
            request.session["password_reset_email"] = email
            return redirect("password_reset")
    else:
        form = PasswordResetRequestForm()
    return render(
        request,
        "accounts/password_reset.html",
        {"form": form, "sent_email": sent_email, "hide_menu": True},
    )


def password_reset_confirm_view(request, uidb64, token):
    user = _decode_user(uidb64, token)
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


# --- 4a 問題投稿画面 ---


@login_required
def problem_new_view(request):
    if request.method == "POST":
        form = ProblemForm(request.POST)
        if form.is_valid():
            problem = form.save(commit=False)
            problem.author = request.user
            problem.save()
            return redirect("problem_created", pk=problem.pk)
    else:
        form = ProblemForm()
    return render(request, "problems/new.html", {"form": form, "show_back": True})


@login_required
def problem_created_view(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    if problem.author_id != request.user.id:
        raise Http404
    return render(
        request,
        "problems/created.html",
        {
            "problem": problem,
            "answer_count": problem.answer_posts.count(),
            "answer_url": _answer_url(request, problem),
            "show_back": True,
        },
    )


# --- 2a 回答投稿画面 ---


def answer_create_view(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    is_open = problem.is_open
    posted = False

    if request.method == "POST":
        # 締切判定はサーバーがこのリクエストを受け取った時刻を基準に行う
        if not is_open:
            return render(
                request,
                "problems/answer.html",
                {
                    "problem": problem,
                    "is_open": False,
                    "form": AnswerPostForm(problem=problem),
                    "show_back": True,
                },
            )
        form = AnswerPostForm(request.POST, problem=problem)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.problem = problem
            answer.save()
            posted = True
            answered = request.session.get("answered_problems", [])
            answered.append(str(problem.pk))
            request.session["answered_problems"] = answered
    else:
        form = AnswerPostForm(problem=problem)

    return render(
        request,
        "problems/answer.html",
        {
            "problem": problem,
            "is_open": is_open,
            "form": form,
            "posted": posted,
            "posted_move": form.cleaned_data.get("move") if posted else "",
            "show_answer_list_link": posted
            and problem.disclosure_type == Problem.AFTER_ANSWER,
            "remaining": _remaining_label(problem.deadline) if is_open else None,
            "show_back": True,
        },
    )


# --- 2b 回答一覧画面 ---


def _can_view_answers(request, problem):
    if request.user.is_authenticated and problem.author_id == request.user.id:
        return True
    if not problem.is_open:
        return True
    if problem.disclosure_type == Problem.AFTER_ANSWER:
        answered = request.session.get("answered_problems", [])
        if str(problem.pk) in answered:
            return True
    return False


def answer_list_view(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    can_view = _can_view_answers(request, problem)
    answers = problem.answer_posts.select_related("rank") if can_view else []
    return render(
        request,
        "answers/list.html",
        {
            "problem": problem,
            "can_view": can_view,
            "answers": answers,
            "show_back": True,
        },
    )


# --- 2c / 2d 問題一覧 ---


@login_required
def active_problems_view(request):
    problems = list(
        Problem.objects.filter(
            author=request.user, closed_at__isnull=True, deadline__gt=timezone.now()
        )
        .annotate(answer_count=Count("answer_posts"))
        .order_by("deadline")
    )
    for problem in problems:
        problem.remaining = _remaining_label(problem.deadline)
        problem.share_url = _answer_url(request, problem)
    return render(request, "problems/active.html", {"problems": problems})


@login_required
def archive_problems_view(request):
    problems = list(
        Problem.objects.filter(author=request.user)
        .filter(Q(closed_at__isnull=False) | Q(deadline__lte=timezone.now()))
        .annotate(answer_count=Count("answer_posts"))
        .order_by("-deadline")
    )
    for problem in problems:
        problem.share_url = _answer_url(request, problem)
    return render(
        request, "problems/archive.html", {"problems": problems, "show_back": True}
    )


@login_required
def problem_close_view(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    problem = get_object_or_404(Problem, pk=pk)
    if problem.author_id != request.user.id:
        raise Http404
    if problem.closed_at is None:
        problem.closed_at = timezone.now()
        problem.save(update_fields=["closed_at"])
    return redirect("active_problems")


@login_required
def problem_delete_view(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    problem = get_object_or_404(Problem, pk=pk)
    if problem.author_id != request.user.id:
        raise Http404
    next_url = request.POST.get("next", "active_problems")
    problem.delete()
    return redirect(next_url if next_url in ("active_problems", "archive_problems") else "active_problems")
