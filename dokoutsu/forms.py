from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import AnswerPost, Problem, Rank

User = get_user_model()


EMAIL_INVALID_MESSAGE = {"invalid": "正しいメールアドレスを入力してください"}


def _placeholder(text):
    return {"placeholder": text}


class SignupForm(forms.Form):
    email = forms.EmailField(
        max_length=254,
        error_messages=EMAIL_INVALID_MESSAGE,
        widget=forms.EmailInput(attrs=_placeholder("you@example.com")),
    )
    username = forms.CharField(
        max_length=150, widget=forms.TextInput(attrs=_placeholder("半角英数字"))
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs=_placeholder("8文字以上の英数字")), min_length=8
    )

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
    login_id = forms.CharField(
        label="IDまたはメールアドレス",
        widget=forms.TextInput(attrs=_placeholder("ID / you@example.com")),
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs=_placeholder("パスワード")))
    remember = forms.BooleanField(required=False)


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        max_length=254,
        error_messages=EMAIL_INVALID_MESSAGE,
        widget=forms.EmailInput(attrs=_placeholder("you@example.com")),
    )


class PasswordResetConfirmForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs=_placeholder("8文字以上の英数字")), min_length=8
    )
    new_password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs=_placeholder("もう一度入力"))
    )

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("new_password"), cleaned.get("new_password_confirm")
        if p1 and not (any(c.isalpha() for c in p1) and any(c.isdigit() for c in p1)):
            self.add_error("new_password", "8文字以上、英字と数字を組み合わせてください")
        if p1 and p2 and p1 != p2:
            self.add_error("new_password_confirm", "パスワードが一致しません")
        return cleaned


HOUR_CHOICES = [(h, f"{h}時") for h in range(24)]
MINUTE_CHOICES = [(m, f"{m:02d}分") for m in range(0, 60, 10)]


class ProblemForm(forms.ModelForm):
    """締切はデザイン(4a)に合わせ、日付・時・分の3つの入力から組み立てる。"""

    title = forms.CharField(
        max_length=100,
        error_messages={"required": "タイトルを入力してください"},
        widget=forms.TextInput(attrs={"placeholder": "例：右辺の攻め合い、どう受ける"}),
    )
    deadline_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    deadline_hour = forms.TypedChoiceField(choices=HOUR_CHOICES, coerce=int, initial=18)
    deadline_minute = forms.TypedChoiceField(choices=MINUTE_CHOICES, coerce=int, initial=0)
    disclosure_type = forms.ChoiceField(
        choices=Problem.DISCLOSURE_CHOICES,
        widget=forms.RadioSelect,
        initial=Problem.AFTER_DEADLINE,
    )
    turn = forms.ChoiceField(
        choices=Problem.TURN_CHOICES, widget=forms.RadioSelect, initial=Problem.BLACK
    )
    board_sgf = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Problem
        fields = ["title", "disclosure_type", "turn", "board_sgf"]

    def clean_board_sgf(self):
        board_sgf = self.cleaned_data["board_sgf"]
        if not board_sgf:
            raise ValidationError("盤面に石を配置してください")
        return board_sgf

    def clean(self):
        import datetime

        from django.utils import timezone

        cleaned = super().clean()
        date = cleaned.get("deadline_date")
        hour = cleaned.get("deadline_hour")
        minute = cleaned.get("deadline_minute")
        if date is None or hour is None or minute is None:
            return cleaned
        deadline = timezone.make_aware(
            datetime.datetime.combine(date, datetime.time(hour, minute))
        )
        if deadline <= timezone.now():
            self.add_error("deadline_date", "締切は現在より後の日時を指定してください")
        else:
            self.instance.deadline = deadline
        return cleaned


class AnswerPostForm(forms.ModelForm):
    nickname = forms.CharField(
        max_length=20,
        error_messages={"required": "ニックネームを入力してください"},
        widget=forms.TextInput(attrs={"placeholder": "ニックネーム"}),
    )
    rank = forms.ModelChoiceField(
        queryset=Rank.objects.all(),
        empty_label="棋力",
        error_messages={"required": "棋力を選択してください"},
    )
    move = forms.CharField(required=False, widget=forms.HiddenInput())
    body = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "コメント"}),
    )

    class Meta:
        model = AnswerPost
        fields = ["nickname", "rank", "move", "body"]

    def clean_move(self):
        move = self.cleaned_data["move"]
        if not move:
            raise ValidationError("着手を1つ選んでください")
        return move
