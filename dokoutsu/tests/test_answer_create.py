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
        problem = self._make_problem(Problem.AFTER_ANSWER, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "n", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertTrue(response.context["show_answer_list_link"])

    def test_after_deadline_type_hides_answer_list_link(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "n", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertFalse(response.context["show_answer_list_link"])

    def test_deadline_passed_shows_message_and_link_on_get(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(seconds=-1))
        response = self.client.get(reverse("answer_create", kwargs={"pk": problem.pk}))
        self.assertContains(response, "締切を過ぎました")
        self.assertContains(response, reverse("answer_list", kwargs={"pk": problem.pk}))

    def test_answer_create_404_for_unknown_problem(self):
        response = self.client.get(
            reverse("answer_create", kwargs={"pk": "11111111-1111-1111-1111-111111111111"})
        )
        self.assertEqual(response.status_code, 404)

    def test_closed_after_deadline_blocks_new_answers(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(seconds=-1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "x", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertEqual(AnswerPost.objects.count(), 0)
        self.assertContains(response, "締切を過ぎました")
        self.assertContains(response, "受付は終了しています")

    def test_empty_move_rejected(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "x", "rank": self.rank.pk, "move": "", "body": ""},
        )
        self.assertContains(response, "着手を1つ選んでください")

    def test_empty_nickname_rejected(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertEqual(AnswerPost.objects.count(), 0)
        self.assertContains(response, "ニックネームを入力してください")

    def test_unselected_rank_rejected(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "x", "rank": "", "move": "qf", "body": ""},
        )
        self.assertEqual(AnswerPost.objects.count(), 0)
        self.assertContains(response, "棋力を選択してください")

    def test_anonymous_can_post_answer(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "x", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertEqual(AnswerPost.objects.count(), 1)
        self.assertContains(response, "投稿しました")

    def test_deadline_judged_by_server_time(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(minutes=1))
        future = timezone.now() + timedelta(minutes=5)
        with mock.patch("django.utils.timezone.now", return_value=future):
            response = self.client.post(
                reverse("answer_create", kwargs={"pk": problem.pk}),
                {"nickname": "x", "rank": self.rank.pk, "move": "qf", "body": ""},
            )
        self.assertEqual(AnswerPost.objects.count(), 0)
        self.assertContains(response, "締切を過ぎました")

class RankCategoryTests(TestCase):
    def test_rank_options_have_category_and_tabs(self):
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
