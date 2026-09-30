"""M 共通メニューとログアウトのテスト(docs/test/M_共通メニュー.md)"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import Problem

User = get_user_model()


class CommonMenuTests(TestCase):
    """M 共通メニュー: 表示条件"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="nao", email="n@example.com", password="pass1234", is_active=True
        )
        self.problem = Problem.objects.create(
            author=self.user, title="問題", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_ANSWER,
        )

    def test_menu_shown_when_logged_in(self):
        """M N1: ログイン中は共通メニューが表示される"""
        self.client.login(username="nao", password="pass1234")
        response = self.client.get(reverse("active_problems"))
        self.assertContains(response, 'aria-label="共通メニュー"')

    def test_menu_shown_on_answer_screens_when_logged_in(self):
        """M N2: ログイン中は回答投稿画面・回答一覧画面でも共通メニューが表示される"""
        self.client.login(username="nao", password="pass1234")
        response = self.client.get(reverse("answer_create", kwargs={"pk": self.problem.pk}))
        self.assertContains(response, 'aria-label="共通メニュー"')
        response = self.client.get(reverse("answer_list", kwargs={"pk": self.problem.pk}))
        self.assertContains(response, 'aria-label="共通メニュー"')

    def test_menu_hidden_when_anonymous(self):
        """M A1: 未ログインでは共通メニューを表示しない"""
        response = self.client.get(reverse("answer_create", kwargs={"pk": self.problem.pk}))
        self.assertNotContains(response, 'aria-label="共通メニュー"')

    def test_menu_hidden_on_auth_screens(self):
        # ログイン済みの場合、これらの画面自体を表示せず受付中の問題一覧へリダイレクトする
        # (詳細設計書「6. セキュリティ上の考慮点」)。結果として共通メニューも表示されない。
        """M A2: ログイン画面・新規登録画面・パスワード再発行画面では共通メニューを表示しない"""
        self.client.login(username="nao", password="pass1234")
        for name in ("login", "signup", "password_reset"):
            response = self.client.get(reverse(name))
            self.assertRedirects(response, reverse("active_problems"))


class LogoutTests(TestCase):
    """M 共通メニュー: ログアウトはPOSTのみ受け付ける"""

    def setUp(self):
        User.objects.create_user(username="lo", email="lo@example.com", password="pass1234")
        self.client.login(username="lo", password="pass1234")

    def test_get_does_not_logout(self):
        """M L1: GETではログアウトしない"""
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.client.get(reverse("active_problems")).status_code, 200)

    def test_post_logs_out(self):
        """M L2: POSTでログアウトする"""
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertRedirects(
            self.client.get(reverse("active_problems")),
            f"{reverse('login')}?next={reverse('active_problems')}",
        )
