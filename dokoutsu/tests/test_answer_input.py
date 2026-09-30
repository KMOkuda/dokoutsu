"""2a 回答投稿画面: 入力値の検証と残り時間の表示のテスト(docs/test/2a_回答投稿画面.md 6・7章)"""

from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import AnswerPost, Problem, Rank

User = get_user_model()


class AnswerInputValidationTests(TestCase):
    def setUp(self):
        author = User.objects.create_user(username="av", email="av@example.com", password="pass1234")
        self.problem = Problem.objects.create(
            author=author, title="問題", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        self.rank = Rank.objects.first()

    def _post(self, **overrides):
        data = {"nickname": "こだぬき", "rank": self.rank.pk, "move": "qf", "body": ""}
        data.update(overrides)
        return self.client.post(reverse("answer_create", kwargs={"pk": self.problem.pk}), data)

    def test_nickname_notice_shown(self):
        response = self.client.get(reverse("answer_create", kwargs={"pk": self.problem.pk}))
        self.assertContains(response, "ニックネームは本人確認されません。")

    def test_nickname_over_20_chars_rejected(self):
        response = self._post(nickname="あ" * 21)
        self.assertContains(response, "20文字以内で入力してください")
        self.assertFalse(AnswerPost.objects.exists())

    def test_body_over_200_chars_rejected(self):
        response = self._post(body="あ" * 201)
        self.assertContains(response, "200文字以内で入力してください")
        self.assertFalse(AnswerPost.objects.exists())

    def test_body_200_chars_accepted(self):
        self._post(body="あ" * 200)
        self.assertEqual(AnswerPost.objects.get().body, "あ" * 200)

    def test_malformed_move_rejected(self):
        for move in ("zz", "q", "qfq", "<b>"):
            with self.subTest(move=move):
                response = self._post(move=move)
                self.assertContains(response, "着手のデータが正しくありません")
        self.assertFalse(AnswerPost.objects.exists())

    def test_move_on_occupied_point_rejected(self):
        response = self._post(move="pd")
        self.assertContains(response, "着手のデータが正しくありません")
        self.assertFalse(AnswerPost.objects.exists())

class RemainingLabelTests(TestCase):
    """締切までの残り表示(詳細設計書 2a「2.2 表示項目」、2c「2.2 表示項目」)。"""

    def _label(self, delta):
        from ..services import remaining_label as _remaining_label

        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            return _remaining_label(now + delta)

    def test_days_hours_minutes(self):
        cases = [
            (timedelta(days=2, hours=5), "2日"),
            (timedelta(hours=24), "1日"),
            (timedelta(hours=23, minutes=59), "23時間"),
            (timedelta(hours=1), "1時間"),
            (timedelta(minutes=59, seconds=59), "59分"),
            (timedelta(minutes=5), "5分"),
            (timedelta(seconds=30), "1分"),
        ]
        for delta, expected in cases:
            with self.subTest(delta=delta):
                self.assertEqual(self._label(delta), expected)

    def test_past_deadline_has_no_label(self):
        self.assertIsNone(self._label(timedelta(seconds=-1)))

    def test_answer_screen_shows_minutes(self):
        author = User.objects.create_user(username="mn", email="mn@example.com", password="pass1234")
        problem = Problem.objects.create(
            author=author, title="分表示", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(minutes=30, seconds=30),
            disclosure_type=Problem.AFTER_DEADLINE,
        )
        response = self.client.get(reverse("answer_create", kwargs={"pk": problem.pk}))
        self.assertContains(response, "締切まであと30分")
