"""2c 受付中の問題一覧・2d 受付終了の問題一覧のテスト(docs/test/2c・2d)"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import AnswerPost, Problem, Rank

User = get_user_model()


class ProblemListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ken", email="k@example.com", password="pass1234", is_active=True
        )
        self.client.login(username="ken", password="pass1234")

    def test_active_and_archive_split(self):
        active = Problem.objects.create(
            author=self.user, title="現役", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        archived = Problem.objects.create(
            author=self.user, title="終了", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() - timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        active_resp = self.client.get(reverse("active_problems"))
        archive_resp = self.client.get(reverse("archive_problems"))
        self.assertIn(active, active_resp.context["problems"])
        self.assertNotIn(archived, active_resp.context["problems"])
        self.assertIn(archived, archive_resp.context["problems"])
        self.assertNotIn(active, archive_resp.context["problems"])

    def test_close_and_delete(self):
        problem = Problem.objects.create(
            author=self.user, title="対象", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        self.client.post(reverse("problem_close", kwargs={"pk": problem.pk}))
        problem.refresh_from_db()
        self.assertIsNotNone(problem.closed_at)

        answer = AnswerPost.objects.create(
            problem=problem, nickname="n", rank=Rank.objects.first(), move="qf"
        )
        self.client.post(reverse("problem_delete", kwargs={"pk": problem.pk}), {"next": "archive_problems"})
        self.assertFalse(Problem.objects.filter(pk=problem.pk).exists())
        self.assertFalse(AnswerPost.objects.filter(pk=answer.pk).exists())

    def test_closing_already_closed_problem_is_noop(self):
        problem = Problem.objects.create(
            author=self.user, title="既に終了", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
            closed_at=timezone.now() - timedelta(hours=1),
        )
        original_closed_at = problem.closed_at
        self.client.post(reverse("problem_close", kwargs={"pk": problem.pk}))
        problem.refresh_from_db()
        self.assertEqual(problem.closed_at, original_closed_at)

    def test_cannot_operate_on_others_problem(self):
        other = User.objects.create_user(username="liz", email="l@example.com", password="pass1234", is_active=True)
        problem = Problem.objects.create(
            author=other, title="他人の問題", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        response = self.client.post(reverse("problem_close", kwargs={"pk": problem.pk}))
        self.assertEqual(response.status_code, 404)
        response = self.client.post(reverse("problem_delete", kwargs={"pk": problem.pk}))
        self.assertEqual(response.status_code, 404)

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("active_problems"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('active_problems')}")
        response = self.client.get(reverse("archive_problems"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('archive_problems')}")

class OrderingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="od", email="od@example.com", password="pass1234")
        self.client.login(username="od", password="pass1234")

    def test_answers_listed_newest_first(self):
        problem = Problem.objects.create(
            author=self.user, title="並び", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        rank = Rank.objects.first()
        first = AnswerPost.objects.create(problem=problem, nickname="先", rank=rank, move="aa")
        second = AnswerPost.objects.create(problem=problem, nickname="後", rank=rank, move="bb")
        AnswerPost.objects.filter(pk=first.pk).update(created_at=timezone.now() - timedelta(hours=1))
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertEqual([a.pk for a in response.context["answers"]], [second.pk, first.pk])

    def test_archive_ordered_by_closed_at_before_deadline(self):
        now = timezone.now()
        # 締切は古いが、今日受付終了した問題 → 終了日時は今日なので先頭に来る
        closed_today = Problem.objects.create(
            author=self.user, title="今日終了", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=now + timedelta(days=5), closed_at=now - timedelta(minutes=5),
            disclosure_type=Problem.AFTER_DEADLINE,
        )
        expired_yesterday = Problem.objects.create(
            author=self.user, title="昨日締切", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=now - timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        expired_last_week = Problem.objects.create(
            author=self.user, title="先週締切", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=now - timedelta(days=7), disclosure_type=Problem.AFTER_DEADLINE,
        )
        response = self.client.get(reverse("archive_problems"))
        self.assertEqual(
            [p.pk for p in response.context["problems"]],
            [closed_today.pk, expired_yesterday.pk, expired_last_week.pk],
        )
