import datetime
import re

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from .models import AnswerPost, Problem, Rank

User = get_user_model()

# Djangoの既定の文言(「このフィールドは必須です。」等)は詳細設計書の文言と異なるため、
# エラーの種類ごとに差し替える。%(limit_value)d には各項目の上限・下限の数値が入る。
REQUIRED_MESSAGE = {"required": "入力してください"}
MAX_LENGTH_MESSAGE = {"max_length": "%(limit_value)d文字以内で入力してください"}
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

# 盤面(Problem.board_sgf)はgoban.jsが「AB[黒石の座標]…AW[白石の座標]…」の形で書き出す。
# 座標は19路盤の列・行をそれぞれa〜sの1文字で表す(SGF形式)。
BOARD_SGF_PATTERN = re.compile(r"(AB(\[[a-s]{2}\])+)?(AW(\[[a-s]{2}\])+)?")
SGF_POINT_PATTERN = re.compile(r"\[([a-s]{2})\]")
MOVE_PATTERN = re.compile(r"[a-s]{2}")


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


HOUR_CHOICES = [(h, f"{h}時") for h in range(24)]
MINUTE_CHOICES = [(m, f"{m:02d}分") for m in range(0, 60, 10)]


class ProblemForm(forms.ModelForm):
    """締切はデザイン(4a)に合わせ、日付・時・分の3つの入力から組み立てる。"""

    title = forms.CharField(
        max_length=100,
        error_messages={"required": "タイトルを入力してください", **MAX_LENGTH_MESSAGE},
        widget=forms.TextInput(attrs={"placeholder": "例：右辺の攻め合い、どう受ける"}),
    )
    deadline_date = forms.DateField(
        error_messages={
            "required": "締切の日付を選択してください",
            "invalid": "締切の日付を選択してください",
        },
        # type="date"の入力欄は「YYYY-MM-DD」形式の値しか表示できないため、形式を固定する
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    deadline_hour = forms.TypedChoiceField(choices=HOUR_CHOICES, coerce=int)
    deadline_minute = forms.TypedChoiceField(choices=MINUTE_CHOICES, coerce=int)
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            # 締切の初期値は、現在時刻より後で最も近い10分刻みの日時(詳細設計書 4a「2.1 入力項目」)。
            # 例: 14:03→14:10、14:10→14:20、23:55→翌日0:00
            now = timezone.localtime().replace(second=0, microsecond=0)
            default = now + datetime.timedelta(minutes=10 - now.minute % 10)
            self.initial.update(
                deadline_date=default.date(),
                deadline_hour=default.hour,
                deadline_minute=default.minute,
            )

    def clean_board_sgf(self):
        board_sgf = self.cleaned_data["board_sgf"]
        if not board_sgf:
            raise ValidationError("盤面に石を配置してください")
        # 画面からは正しい形式しか送られないため、形式違いは改ざんされた送信とみなす
        points = SGF_POINT_PATTERN.findall(board_sgf)
        if not BOARD_SGF_PATTERN.fullmatch(board_sgf) or len(points) != len(set(points)):
            raise ValidationError("盤面のデータが正しくありません")
        return board_sgf

    def clean(self):
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


class RankSelect(forms.Select):
    """棋力のプルダウン。画面の「級」「段」タブで絞り込めるよう、選択肢ごとに区分を持たせる。"""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        # 先頭の「棋力」(未選択)は区分を持たない。それ以外のvalueからは元のRankを取り出せる
        if value:
            option["attrs"]["data-category"] = value.instance.category
        return option


class AnswerPostForm(forms.ModelForm):
    nickname = forms.CharField(
        max_length=20,
        error_messages={"required": "ニックネームを入力してください", **MAX_LENGTH_MESSAGE},
        widget=forms.TextInput(attrs={"placeholder": "ニックネーム"}),
    )
    rank = forms.ModelChoiceField(
        queryset=Rank.objects.all(),
        empty_label="棋力",
        error_messages={"required": "棋力を選択してください"},
        widget=RankSelect,
    )
    move = forms.CharField(required=False, widget=forms.HiddenInput())
    body = forms.CharField(
        required=False,
        max_length=200,
        error_messages=MAX_LENGTH_MESSAGE,
        widget=forms.TextInput(attrs={"placeholder": "コメント"}),
    )

    class Meta:
        model = AnswerPost
        fields = ["nickname", "rank", "move", "body"]

    def __init__(self, *args, problem, **kwargs):
        # 着手が空いている交点かを判定するため、回答先の問題の盤面を受け取る
        super().__init__(*args, **kwargs)
        self.problem = problem

    def clean_move(self):
        move = self.cleaned_data["move"]
        if not move:
            raise ValidationError("着手を1つ選んでください")
        occupied = SGF_POINT_PATTERN.findall(self.problem.board_sgf)
        if not MOVE_PATTERN.fullmatch(move) or move in occupied:
            raise ValidationError("着手のデータが正しくありません")
        return move
