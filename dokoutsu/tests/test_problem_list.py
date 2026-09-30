"""2c 受付中の問題一覧・2d 受付終了の問題一覧のテスト(docs/test/2c・2d)"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import AnswerPost, Problem, Rank

User = get_user_model()


class ProblemListTests(TestCase):
    """2c・2d 問題一覧: 絞り込み・受付終了・削除・権限"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="ken", email="k@example.com", password="pass1234", is_active=True
        )
        self.client.login(username="ken", password="pass1234")

    def test_active_and_archive_split(self):
        """2c N1: 自分の受付中の問題だけが表示される / 2d N1: 自分の受付終了の問題だけが表示される"""
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
        # response.context: ビューが画面(テンプレート)に渡した値。表示の元になる値を直接確かめる
        self.assertIn(active, active_resp.context["problems"])
        self.assertNotIn(archived, active_resp.context["problems"])
        self.assertIn(archived, archive_resp.context["problems"])
        self.assertNotIn(active, archive_resp.context["problems"])

    def test_close_and_delete(self):
        """2c N2: 出題を終了できる / 2c N3: 問題を削除できる / 2d N2: 問題を削除できる"""
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
        """2c E2: 既に受付終了済みの問題への終了操作"""
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
        """2c E1: 他人の問題への操作 / 2d E1: 他人の問題への操作"""
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
        """2c A1: 未ログインでは閲覧できない / 4a A1: 未ログインでは問題を作成できない / 2d A1: 未ログインでは閲覧できない"""
        self.client.logout()
        response = self.client.get(reverse("active_problems"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('active_problems')}")
        response = self.client.get(reverse("archive_problems"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('archive_problems')}")


class OrderingTests(TestCase):
    """2b・2d 並び順(回答は新しい順、受付終了の問題は終了日時の新しい順)"""

    def setUp(self):
        self.user = User.objects.create_user(username="od", email="od@example.com", password="pass1234")
        self.client.login(username="od", password="pass1234")

    def test_answers_listed_newest_first(self):
        """2b D1: 回答の並び順"""
        problem = Problem.objects.create(
            author=self.user, title="並び", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        rank = Rank.objects.first()
        first = AnswerPost.objects.create(problem=problem, nickname="先", rank=rank, move="aa")
        second = AnswerPost.objects.create(problem=problem, nickname="後", rank=rank, move="bb")
        # 記録の日時を過去にずらし、期間が過ぎた状態を作る
        AnswerPost.objects.filter(pk=first.pk).update(created_at=timezone.now() - timedelta(hours=1))
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertEqual([a.pk for a in response.context["answers"]], [second.pk, first.pk])

    def test_archive_shows_deadline_or_closed_label(self):
        """2d D2: 締切を過ぎた問題は「に締切」、出題者が受付を終了させた問題は「に受付を終了」と表示する"""
        now = timezone.localtime()
        Problem.objects.create(
            author=self.user, title="締切で終了", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=now - timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        closed_at = now - timedelta(hours=2)
        Problem.objects.create(
            author=self.user, title="出題者が終了", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=now + timedelta(days=3), closed_at=closed_at,
            disclosure_type=Problem.AFTER_DEADLINE,
        )
        response = self.client.get(reverse("archive_problems"))
        deadline_label = timezone.localtime(now - timedelta(days=1)).strftime("%-m月%-d日 %H:%M") + " に締切"
        closed_label = timezone.localtime(closed_at).strftime("%-m月%-d日 %H:%M") + " に受付を終了"
        self.assertContains(response, deadline_label)
        self.assertContains(response, closed_label)
        self.assertNotContains(response, " に終了")

    def test_archive_ordered_by_closed_at_before_deadline(self):
        """2d D1: 問題の並び順"""
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
