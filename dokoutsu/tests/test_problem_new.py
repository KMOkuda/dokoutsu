"""4a 問題投稿画面のテスト(docs/test/4a_問題投稿画面.md)"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import Problem

User = get_user_model()


class ProblemTests(TestCase):
    """4a 問題投稿: 出題と出題完了画面、エラー"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="hana", email="h@example.com", password="pass1234", is_active=True
        )
        self.client.login(username="hana", password="pass1234")

    def test_create_problem_redirects_to_created(self):
        """4a N1: 問題を作成すると出題完了画面へ遷移する"""
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
        """4a N2: 出題完了画面は出題者本人が閲覧できる"""
        problem = Problem.objects.create(
            author=self.user, title="表示確認", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        response = self.client.get(reverse("problem_created", kwargs={"pk": problem.pk}))
        self.assertContains(response, "表示確認")
        # response.context: ビューが画面(テンプレート)に渡した値。表示の元になる値を直接確かめる
        self.assertEqual(response.context["answer_count"], 0)

    def test_empty_title_rejected(self):
        """4a E1: タイトル未入力"""
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
        """4a E2: 締切が過去日時"""
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
        """4a E3: 盤面未入力"""
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
        """4a E4: 出題完了画面: 存在しない問題ID"""
        response = self.client.get(
            reverse("problem_created", kwargs={"pk": "11111111-1111-1111-1111-111111111111"})
        )
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_view_created_page(self):
        """4a E5: 出題完了画面: 他人の問題"""
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
        """2c A1: 未ログインでは閲覧できない / 4a A1: 未ログインでは問題を作成できない / 2d A1: 未ログインでは閲覧できない"""
        self.client.logout()
        response = self.client.get(reverse("problem_new"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('problem_new')}")


class ProblemInputValidationTests(TestCase):
    """4a 問題投稿: 入力値の検証(タイトルの文字数・締切・盤面データの形式)"""

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
        """4a V1: 正しい盤面"""
        response = self._post()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Problem.objects.get().board_sgf, "AB[pd]AW[dd]")

    def test_title_over_100_chars_rejected(self):
        """4a V2: タイトルが上限超過"""
        response = self._post(title="あ" * 101)
        self.assertContains(response, "100文字以内で入力してください")
        self.assertFalse(Problem.objects.exists())

    def test_title_100_chars_accepted(self):
        """4a V3: タイトルが上限ちょうど"""
        response = self._post(title="あ" * 100)
        self.assertEqual(response.status_code, 302)

    def test_empty_deadline_date_shows_message(self):
        """4a V4: 締切の日付未選択"""
        response = self._post(deadline_date="")
        self.assertContains(response, "締切の日付を選択してください")

    def test_malformed_board_rejected(self):
        # 範囲外の座標(t以降)、SGF以外の文字列、同じ交点への重複配置、AWとABの順序違い
        """4a V5: 盤面データの形式不正"""
        for board in ("AB[zz]", "<script>alert(1)</script>", "AB[pd]AW[pd]", "AW[dd]AB[pd]", "AB[pd"):
            # subTest: 1つのテストの中で複数の値を試し、失敗した場合はどの値で失敗したかを個別に報告させる
            with self.subTest(board=board):
                response = self._post(board_sgf=board)
                self.assertContains(response, "盤面のデータが正しくありません")
        self.assertFalse(Problem.objects.exists())
