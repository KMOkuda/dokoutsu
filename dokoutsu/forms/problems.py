"""4a 問題投稿・2a 回答投稿のフォーム"""

import datetime
import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import AnswerPost, Problem, Rank
from .messages import MAX_LENGTH_MESSAGE

# 盤面(Problem.board_sgf)はgoban_board.jsが「AB[黒石の座標]…AW[白石の座標]…」の形で書き出す。
# 座標は19路盤の列・行をそれぞれa〜sの1文字で表す(SGF形式)。
BOARD_SGF_PATTERN = re.compile(r"(AB(\[[a-s]{2}\])+)?(AW(\[[a-s]{2}\])+)?")
SGF_POINT_PATTERN = re.compile(r"\[([a-s]{2})\]")
MOVE_PATTERN = re.compile(r"[a-s]{2}")



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
