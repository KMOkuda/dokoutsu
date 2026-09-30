"""2b 回答一覧画面のテスト(docs/test/2b_回答一覧画面.md)"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import AnswerPost, Problem, Rank

User = get_user_model()


class AnswerListVisibilityTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username="jun", email="j@example.com", password="pass1234", is_active=True
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

    def test_author_can_always_view(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        self.client.login(username="jun", password="pass1234")
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertTrue(response.context["can_view"])

    def test_public_after_deadline_regardless_of_type(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(seconds=-1))
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertTrue(response.context["can_view"])

    def test_after_answer_type_visible_once_answered_in_session(self):
        problem = self._make_problem(Problem.AFTER_ANSWER, timedelta(days=1))
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertFalse(response.context["can_view"])

        self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "こだぬき", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertTrue(response.context["can_view"])
        self.assertEqual(AnswerPost.objects.count(), 1)

    def test_empty_answer_list_shows_placeholder(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(seconds=-1))
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertContains(response, "まだ回答がありません")

    def test_answer_list_404_for_unknown_problem(self):
        response = self.client.get(
            reverse("answer_list", kwargs={"pk": "11111111-1111-1111-1111-111111111111"})
        )
        self.assertEqual(response.status_code, 404)

    def test_after_deadline_type_hidden_before_deadline_for_stranger(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertFalse(response.context["can_view"])
        self.assertContains(response, "回答は締切後に公開されます")
