from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import AnswerPost, Problem, Rank

User = get_user_model()


EMAIL_INVALID_MESSAGE = {"invalid": "正しいメールアドレスを入力してください"}


class SignupForm(forms.Form):
    email = forms.EmailField(max_length=254, error_messages=EMAIL_INVALID_MESSAGE)
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise ValidationError("このメールアドレスは既に登録されています")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"]
        if not username.isalnum():
            raise ValidationError("IDは半角英数字で入力してください")
        if User.objects.filter(username=username).exists():
            raise ValidationError("このIDは既に使用されています")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not (any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
            raise ValidationError("8文字以上、英字と数字を組み合わせてください")
        return password

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            is_active=False,
        )
        return user


class LoginForm(forms.Form):
    login_id = forms.CharField(label="IDまたはメールアドレス")
    password = forms.CharField(widget=forms.PasswordInput)
    remember = forms.BooleanField(required=False)


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(max_length=254, error_messages=EMAIL_INVALID_MESSAGE)


class PasswordResetConfirmForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    new_password_confirm = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("new_password"), cleaned.get("new_password_confirm")
        if p1 and not (any(c.isalpha() for c in p1) and any(c.isdigit() for c in p1)):
            self.add_error("new_password", "8文字以上、英字と数字を組み合わせてください")
        if p1 and p2 and p1 != p2:
            self.add_error("new_password_confirm", "パスワードが一致しません")
        return cleaned


class ProblemForm(forms.ModelForm):
    board_sgf = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Problem
        fields = ["title", "deadline", "disclosure_type", "turn", "board_sgf"]
        widgets = {
            "deadline": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "turn": forms.RadioSelect(),
            "disclosure_type": forms.RadioSelect(),
        }

    def clean_board_sgf(self):
        board_sgf = self.cleaned_data["board_sgf"]
        if not board_sgf:
            raise ValidationError("盤面に石を配置してください")
        return board_sgf

    def clean_deadline(self):
        from django.utils import timezone

        deadline = self.cleaned_data["deadline"]
        if deadline <= timezone.now():
            raise ValidationError("締切は現在より後の日時を指定してください")
        return deadline


class AnswerPostForm(forms.ModelForm):
    rank = forms.ModelChoiceField(queryset=Rank.objects.all(), empty_label="選択してください")
    move = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = AnswerPost
        fields = ["nickname", "rank", "move", "body"]

    def clean_move(self):
        move = self.cleaned_data["move"]
        if not move:
            raise ValidationError("着手を1つ選んでください")
        return move
