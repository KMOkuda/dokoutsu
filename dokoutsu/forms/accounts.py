"""3a 新規登録・3b ログイン・6a パスワード再発行のフォーム"""

import re

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q

from .messages import MAX_LENGTH_MESSAGE, REQUIRED_MESSAGE

User = get_user_model()

EMAIL_MESSAGES = {
    **REQUIRED_MESSAGE,
    **MAX_LENGTH_MESSAGE,
    "invalid": "正しいメールアドレスを入力してください",
}
PASSWORD_RULE_MESSAGE = "8文字以上、英字と数字を組み合わせてください"
PASSWORD_MESSAGES = {**REQUIRED_MESSAGE, **MAX_LENGTH_MESSAGE, "min_length": PASSWORD_RULE_MESSAGE}

# str.isalnum()/isalpha()/isdigit()は日本語や全角数字も英数字とみなすため、半角に限定して判定する
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9]+")
HAS_ALPHABET = re.compile(r"[A-Za-z]")
HAS_DIGIT = re.compile(r"[0-9]")

def _placeholder(text):
    return {"placeholder": text}


def _is_valid_password(password):
    return bool(HAS_ALPHABET.search(password) and HAS_DIGIT.search(password))


class SignupForm(forms.Form):
    email = forms.EmailField(
        max_length=254,
        error_messages=EMAIL_MESSAGES,
        widget=forms.EmailInput(attrs=_placeholder("you@example.com")),
    )
    username = forms.CharField(
        max_length=150,
        error_messages={**REQUIRED_MESSAGE, **MAX_LENGTH_MESSAGE},
        widget=forms.TextInput(attrs=_placeholder("半角英数字")),
    )
    password = forms.CharField(
        min_length=8,
        max_length=128,
        error_messages=PASSWORD_MESSAGES,
        widget=forms.PasswordInput(attrs=_placeholder("8文字以上の英数字")),
    )

    # メールアドレス・IDの重複は、確認済み(is_active=True)のアカウントとだけ比べる。
    # 確認メールのリンクを開かずに期限が切れた人が、同じメールアドレス・IDで登録し直せるようにするため
    # (詳細設計書 3a「7. この画面固有の設計事項」)
    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email, is_active=True).exists():
            raise ValidationError("このメールアドレスは既に登録されています")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"]
        if not USERNAME_PATTERN.fullmatch(username):
            raise ValidationError("IDは半角英数字で入力してください")
        if User.objects.filter(username=username, is_active=True).exists():
            raise ValidationError("このIDは既に使用されています")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not _is_valid_password(password):
            raise ValidationError(PASSWORD_RULE_MESSAGE)
        return password

    def save(self):
        # 同じメールアドレスまたはIDの未確認アカウントは、新しい登録で置き換える。
        # 前の確認リンクは、対象のアカウントがなくなるため使えなくなる
        User.objects.filter(is_active=False).filter(
            Q(email=self.cleaned_data["email"]) | Q(username=self.cleaned_data["username"])
        ).delete()
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            is_active=False,
        )
        return user


class LoginForm(forms.Form):
    login_id = forms.CharField(
        max_length=254,
        error_messages={**REQUIRED_MESSAGE, **MAX_LENGTH_MESSAGE},
        widget=forms.TextInput(attrs=_placeholder("ID / you@example.com")),
    )
    password = forms.CharField(
        max_length=128,
        error_messages={**REQUIRED_MESSAGE, **MAX_LENGTH_MESSAGE},
        widget=forms.PasswordInput(attrs=_placeholder("パスワード")),
    )
    remember = forms.BooleanField(required=False)


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        max_length=254,
        error_messages=EMAIL_MESSAGES,
        widget=forms.EmailInput(attrs=_placeholder("you@example.com")),
    )


class PasswordResetConfirmForm(forms.Form):
    new_password = forms.CharField(
        min_length=8,
        max_length=128,
        error_messages=PASSWORD_MESSAGES,
        widget=forms.PasswordInput(attrs=_placeholder("8文字以上の英数字")),
    )
    new_password_confirm = forms.CharField(
        max_length=128,
        error_messages={**REQUIRED_MESSAGE, **MAX_LENGTH_MESSAGE},
        widget=forms.PasswordInput(attrs=_placeholder("もう一度入力")),
    )

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("new_password"), cleaned.get("new_password_confirm")
        if p1 and not _is_valid_password(p1):
            self.add_error("new_password", PASSWORD_RULE_MESSAGE)
        if p1 and p2 and p1 != p2:
            self.add_error("new_password_confirm", "パスワードが一致しません")
        return cleaned
