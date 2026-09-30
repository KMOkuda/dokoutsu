"""2a 回答投稿画面のテスト(docs/test/2a_回答投稿画面.md)"""

from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import AnswerPost, Problem, Rank

User = get_user_model()


class AnswerCreateTests(TestCase):
    """2a 回答投稿: 投稿・受付終了後の表示・エラー"""

    def setUp(self):
        self.author = User.objects.create_user(
            username="mika", email="m@example.com", password="pass1234", is_active=True
        )
        self.rank = Rank.objects.first()

    def _make_problem(self, disclosure_type, deadline_delta):
        return Problem.objects.create(
            author=self.author,
            title="問題",
            board_sgf="AB[pd]",
            turn=Problem.BLACK,
            deadline=timezone.now() + deadline_delta,
            disclosure_type=disclosure_type,
        )

    def test_after_answer_type_shows_answer_list_link(self):
        """2a N2: disclosure_typeがafter_answerの場合、投稿後にみんなの回答を見るボタンが表示される"""
        problem = self._make_problem(Problem.AFTER_ANSWER, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "n", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        # response.context: ビューが画面(テンプレート)に渡した値。表示の元になる値を直接確かめる
        self.assertTrue(response.context["show_answer_list_link"])

    def test_after_deadline_type_hides_answer_list_link(self):
        """2a N3: disclosure_typeがafter_deadlineの場合、投稿後は締切後にシェアされる旨のみ表示する"""
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "n", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertFalse(response.context["show_answer_list_link"])

    def test_deadline_passed_shows_message_and_link_on_get(self):
        """2a N4: 締切を過ぎた問題を開くと「締切を過ぎました」とボタンが表示される"""
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(seconds=-1))
        response = self.client.get(reverse("answer_create", kwargs={"pk": problem.pk}))
        self.assertContains(response, "締切を過ぎました")
        self.assertContains(response, reverse("answer_list", kwargs={"pk": problem.pk}))

    def test_answer_create_404_for_unknown_problem(self):
        """2a E1: 存在しない問題ID"""
        response = self.client.get(
            reverse("answer_create", kwargs={"pk": "11111111-1111-1111-1111-111111111111"})
        )
        self.assertEqual(response.status_code, 404)

    def test_closed_after_deadline_blocks_new_answers(self):
        """2a E2: 受付終了後の投稿"""
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(seconds=-1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "x", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertEqual(AnswerPost.objects.count(), 0)
        self.assertContains(response, "締切を過ぎました")
        self.assertContains(response, "受付は終了しています")

    def test_empty_move_rejected(self):
        """2a E3: 着手未入力"""
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "x", "rank": self.rank.pk, "move": "", "body": ""},
        )
        self.assertContains(response, "着手を1つ選んでください")

    def test_empty_nickname_rejected(self):
        """2a E4: ニックネーム未入力"""
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertEqual(AnswerPost.objects.count(), 0)
        self.assertContains(response, "ニックネームを入力してください")

    def test_unselected_rank_rejected(self):
        """2a E5: 棋力未選択"""
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "x", "rank": "", "move": "qf", "body": ""},
        )
        self.assertEqual(AnswerPost.objects.count(), 0)
        self.assertContains(response, "棋力を選択してください")

    def test_anonymous_can_post_answer(self):
        """2a N1: 受付中の問題に回答を投稿できる / 2a A1: 未ログインでも回答を投稿できる"""
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "x", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertEqual(AnswerPost.objects.count(), 1)
        self.assertContains(response, "投稿しました")

    def test_deadline_judged_by_server_time(self):
        """2a A2: 締切内かどうかはサーバーの受信時刻で判定する"""
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(minutes=1))
        future = timezone.now() + timedelta(minutes=5)
        # 締切の1分前に作った問題に、サーバーの現在時刻を5分後へ進めた状態で投稿する。
        # 画面の残り時間ではなく、サーバーが受け取った時刻で締切を判定することを確かめる
        with mock.patch("django.utils.timezone.now", return_value=future):
            response = self.client.post(
                reverse("answer_create", kwargs={"pk": problem.pk}),
                {"nickname": "x", "rank": self.rank.pk, "move": "qf", "body": ""},
            )
        self.assertEqual(AnswerPost.objects.count(), 0)
        self.assertContains(response, "締切を過ぎました")


class RankCategoryTests(TestCase):
    """2a 回答投稿: 棋力の級/段タブ"""

    def test_rank_options_have_category_and_tabs(self):
        """2a S1: 棋力の級/段タブ"""
        author = User.objects.create_user(username="rk", email="rk@example.com", password="pass1234")
        problem = Problem.objects.create(
            author=author, title="棋力", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        response = self.client.get(reverse("answer_create", kwargs={"pk": problem.pk}))
        self.assertContains(response, 'data-rank-category="kyu"')
        self.assertContains(response, 'data-rank-category="dan"')
        self.assertContains(response, 'data-category="kyu"', count=Rank.objects.filter(category=Rank.KYU).count())
        self.assertContains(response, 'data-category="dan"', count=Rank.objects.filter(category=Rank.DAN).count())
