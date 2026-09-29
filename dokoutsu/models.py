import uuid

from django.conf import settings
from django.db import models


class Rank(models.Model):
    """棋力の選択肢マスタ(テーブル定義書 2.4 dokoutsu_rank)"""

    KYU = "kyu"
    DAN = "dan"
    CATEGORY_CHOICES = [(KYU, "級"), (DAN, "段")]

    label = models.CharField(max_length=5)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    sort_order = models.IntegerField()

    class Meta:
        db_table = "dokoutsu_rank"
        ordering = ["sort_order"]

    def __str__(self):
        return self.label


class Problem(models.Model):
    """問題(テーブル定義書 2.2 dokoutsu_problem)"""

    BLACK = "black"
    WHITE = "white"
    TURN_CHOICES = [(BLACK, "黒番"), (WHITE, "白番")]

    AFTER_DEADLINE = "after_deadline"
    AFTER_ANSWER = "after_answer"
    DISCLOSURE_CHOICES = [
        (AFTER_DEADLINE, "締切後に公開URLをシェア"),
        (AFTER_ANSWER, "回答後に公開リンクを表示"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="problems"
    )
    title = models.CharField(max_length=100)
    board_sgf = models.TextField()
    turn = models.CharField(max_length=5, choices=TURN_CHOICES)
    deadline = models.DateTimeField()
    disclosure_type = models.CharField(max_length=20, choices=DISCLOSURE_CHOICES)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dokoutsu_problem"

    def __str__(self):
        return self.title

    @property
    def is_open(self):
        """受付中かどうか(基本設計書 3. 要件の実現方式)"""
        from django.utils import timezone

        return self.closed_at is None and self.deadline > timezone.now()


class AnswerPost(models.Model):
    """回答投稿(テーブル定義書 2.3 dokoutsu_answerpost)"""

    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="answer_posts"
    )
    nickname = models.CharField(max_length=20)
    rank = models.ForeignKey(Rank, on_delete=models.PROTECT)
    move = models.TextField()
    body = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dokoutsu_answerpost"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.nickname} - {self.problem.title}"


class EmailSendLog(models.Model):
    """メール送信の記録(テーブル定義書 2.5 dokoutsu_emailsendlog)。送信回数の制限に使う。"""

    SIGNUP = "signup"
    PASSWORD_RESET = "password_reset"
    PURPOSE_CHOICES = [(SIGNUP, "登録確認"), (PASSWORD_RESET, "パスワード再発行")]

    email = models.EmailField(max_length=254)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dokoutsu_emailsendlog"
        indexes = [models.Index(fields=["email", "purpose", "created_at"])]
