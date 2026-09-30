"""4a 問題投稿画面のテスト(docs/test/4a_問題投稿画面.md)"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import Problem

User = get_user_model()


class ProblemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="hana", email="h@example.com", password="pass1234", is_active=True
        )
        self.client.login(username="hana", password="pass1234")

    def test_create_problem_redirects_to_created(self):
        deadline_date = (timezone.localtime() + timedelta(days=1)).date().isoformat()
        response = self.client.post(
            reverse("problem_new"),
            {
                "title": "テスト問題",
                "deadline_date": deadline_date,
                "deadline_hour": 12,
                "deadline_minute": 0,
                "disclosure_type": Problem.AFTER_DEADLINE,
                "turn": Problem.BLACK,
                "board_sgf": "AB[pd]",
            },
        )
        problem = Problem.objects.get(title="テスト問題")
        self.assertRedirects(response, reverse("problem_created", kwargs={"pk": problem.pk}))
        self.assertEqual(problem.author, self.user)

    def test_created_page_shows_problem_details(self):
        problem = Problem.objects.create(
            author=self.user, title="表示確認", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        response = self.client.get(reverse("problem_created", kwargs={"pk": problem.pk}))
        self.assertContains(response, "表示確認")
        self.assertEqual(response.context["answer_count"], 0)

    def test_empty_title_rejected(self):
        deadline_date = (timezone.localtime() + timedelta(days=1)).date().isoformat()
        response = self.client.post(
            reverse("problem_new"),
            {
                "title": "",
                "deadline_date": deadline_date,
                "deadline_hour": 12,
                "deadline_minute": 0,
                "disclosure_type": Problem.AFTER_DEADLINE,
                "turn": Problem.BLACK,
                "board_sgf": "AB[pd]",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 0)

    def test_past_deadline_rejected(self):
        deadline_date = (timezone.localtime() - timedelta(days=1)).date().isoformat()
        response = self.client.post(
            reverse("problem_new"),
            {
                "title": "過去締切",
                "deadline_date": deadline_date,
                "deadline_hour": 12,
                "deadline_minute": 0,
                "disclosure_type": Problem.AFTER_DEADLINE,
                "turn": Problem.BLACK,
                "board_sgf": "AB[pd]",
            },
        )
        self.assertContains(response, "締切は現在より後の日時を指定してください")

    def test_empty_board_rejected(self):
        deadline_date = (timezone.localtime() + timedelta(days=1)).date().isoformat()
        response = self.client.post(
            reverse("problem_new"),
            {
                "title": "盤面なし",
                "deadline_date": deadline_date,
                "deadline_hour": 12,
                "deadline_minute": 0,
                "disclosure_type": Problem.AFTER_DEADLINE,
                "turn": Problem.BLACK,
                "board_sgf": "",
            },
        )
        self.assertContains(response, "盤面に石を配置してください")

    def test_created_page_404_for_unknown_problem(self):
        response = self.client.get(
            reverse("problem_created", kwargs={"pk": "11111111-1111-1111-1111-111111111111"})
        )
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_view_created_page(self):
        problem = Problem.objects.create(
            author=self.user,
            title="他人の問題",
            board_sgf="AB[pd]",
            turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1),
            disclosure_type=Problem.AFTER_DEADLINE,
        )
        User.objects.create_user(username="ivy", email="i@example.com", password="pass1234", is_active=True)
        self.client.login(username="ivy", password="pass1234")
        response = self.client.get(reverse("problem_created", kwargs={"pk": problem.pk}))
        self.assertEqual(response.status_code, 404)

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("problem_new"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('problem_new')}")

class ProblemInputValidationTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="pv", email="pv@example.com", password="pass1234")
        self.client.login(username="pv", password="pass1234")

    def _post(self, **overrides):
        data = {
            "title": "検証",
            "deadline_date": (timezone.localtime() + timedelta(days=1)).date().isoformat(),
            "deadline_hour": 12,
            "deadline_minute": 0,
            "disclosure_type": Problem.AFTER_DEADLINE,
            "turn": Problem.BLACK,
            "board_sgf": "AB[pd]AW[dd]",
        }
        data.update(overrides)
        return self.client.post(reverse("problem_new"), data)

    def test_valid_board_accepted(self):
        response = self._post()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Problem.objects.get().board_sgf, "AB[pd]AW[dd]")

    def test_title_over_100_chars_rejected(self):
        response = self._post(title="あ" * 101)
        self.assertContains(response, "100文字以内で入力してください")
        self.assertFalse(Problem.objects.exists())

    def test_title_100_chars_accepted(self):
        response = self._post(title="あ" * 100)
        self.assertEqual(response.status_code, 302)

    def test_empty_deadline_date_shows_message(self):
        response = self._post(deadline_date="")
        self.assertContains(response, "締切の日付を選択してください")

    def test_malformed_board_rejected(self):
        # 範囲外の座標(t以降)、SGF以外の文字列、同じ交点への重複配置、AWとABの順序違い
        for board in ("AB[zz]", "<script>alert(1)</script>", "AB[pd]AW[pd]", "AW[dd]AB[pd]", "AB[pd"):
            with self.subTest(board=board):
                response = self._post(board_sgf=board)
                self.assertContains(response, "盤面のデータが正しくありません")
        self.assertFalse(Problem.objects.exists())
