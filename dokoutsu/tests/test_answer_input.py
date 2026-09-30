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
    """2a 回答投稿: 入力値の検証(文字数・着手データの形式)とニックネームの注意書き"""

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
        """2a V1: ニックネームの注意書き"""
        response = self.client.get(reverse("answer_create", kwargs={"pk": self.problem.pk}))
        self.assertContains(response, "ニックネームは本人確認されません。")

    def test_nickname_over_20_chars_rejected(self):
        """2a V2: ニックネームが上限超過"""
        response = self._post(nickname="あ" * 21)
        self.assertContains(response, "20文字以内で入力してください")
        self.assertFalse(AnswerPost.objects.exists())

    def test_body_over_200_chars_rejected(self):
        """2a V3: コメントが上限超過"""
        response = self._post(body="あ" * 201)
        self.assertContains(response, "200文字以内で入力してください")
        self.assertFalse(AnswerPost.objects.exists())

    def test_body_200_chars_accepted(self):
        """2a V4: コメントが上限ちょうど"""
        self._post(body="あ" * 200)
        self.assertEqual(AnswerPost.objects.get().body, "あ" * 200)

    def test_malformed_move_rejected(self):
        """2a V5: 着手データの形式不正"""
        for move in ("zz", "q", "qfq", "<b>"):
            # subTest: 1つのテストの中で複数の値を試し、失敗した場合はどの値で失敗したかを個別に報告させる
            with self.subTest(move=move):
                response = self._post(move=move)
                self.assertContains(response, "着手のデータが正しくありません")
        self.assertFalse(AnswerPost.objects.exists())

    def test_move_on_occupied_point_rejected(self):
        """2a V6: 石がある交点への着手"""
        response = self._post(move="pd")
        self.assertContains(response, "着手のデータが正しくありません")
        self.assertFalse(AnswerPost.objects.exists())


class RemainingLabelTests(TestCase):
    """締切までの残り表示(詳細設計書 2a「2.2 表示項目」、2c「2.2 表示項目」)。"""

    def _label(self, delta):
        from ..services import remaining_label as _remaining_label

        now = timezone.now()
        # サーバーの現在時刻を固定し、実行するたびに結果が変わらないようにする
        with mock.patch("django.utils.timezone.now", return_value=now):
            return _remaining_label(now + delta)

    def test_days_hours_minutes(self):
        """2a S4: 残り表示の単位の切り替え / 2c S1: 残り期間の単位の切り替え"""
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
        """2a S5: 受付終了の問題(締切を過ぎた/受付を終了した)では残り時間を表示せず「締切を過ぎました」を表示する"""
        author = User.objects.create_user(username="pd", email="pd@example.com", password="pass1234")
        expired = Problem.objects.create(
            author=author, title="締切超過", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() - timedelta(seconds=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        # 締切前でも、出題者が受付を終了した(closed_atを設定した)問題は受付終了として扱う
        closed = Problem.objects.create(
            author=author, title="受付終了", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), closed_at=timezone.now(),
            disclosure_type=Problem.AFTER_DEADLINE,
        )
        for problem in (expired, closed):
            with self.subTest(title=problem.title):
                response = self.client.get(reverse("answer_create", kwargs={"pk": problem.pk}))
                self.assertNotContains(response, "締切まであと")
                self.assertContains(response, "締切を過ぎました")

    def test_answer_screen_shows_minutes(self):
        """2a S3: 残り1時間未満は分で表示"""
        author = User.objects.create_user(username="mn", email="mn@example.com", password="pass1234")
        problem = Problem.objects.create(
            author=author, title="分表示", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(minutes=30, seconds=30),
            disclosure_type=Problem.AFTER_DEADLINE,
        )
        response = self.client.get(reverse("answer_create", kwargs={"pk": problem.pk}))
        self.assertContains(response, "締切まであと30分")
