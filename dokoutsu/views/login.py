"""3b ログイン画面と、共通メニューのログアウト(詳細設計書 3b・M)"""

from django.contrib.auth import authenticate, get_user_model, login as auth_login, logout as auth_logout
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render

from ..forms import LoginForm

User = get_user_model()


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
