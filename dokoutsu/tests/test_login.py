"""3b ログイン画面のテスト(docs/test/3b_ログイン画面.md)"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="erin", email="e@example.com", password="pass1234", is_active=True
        )

    def test_login_with_username(self):
        response = self.client.post(
            reverse("login"), {"login_id": "erin", "password": "pass1234"}
        )
        self.assertRedirects(response, reverse("active_problems"))

    def test_login_with_email(self):
        response = self.client.post(
            reverse("login"), {"login_id": "e@example.com", "password": "pass1234"}
        )
        self.assertRedirects(response, reverse("active_problems"))

    def test_remember_unchecked_sets_session_expire_at_browser_close(self):
        self.client.post(
            reverse("login"), {"login_id": "erin", "password": "pass1234"}
        )
        self.assertEqual(self.client.session.get_expire_at_browser_close(), True)

    def test_login_wrong_password(self):
        response = self.client.post(
            reverse("login"), {"login_id": "erin", "password": "wrong"}
        )
        self.assertContains(response, "IDまたはパスワードが違います")

    def test_inactive_user_blocked(self):
        User.objects.create_user(
            username="frank", email="f@example.com", password="pass1234", is_active=False
        )
        response = self.client.post(
            reverse("login"), {"login_id": "frank", "password": "pass1234"}
        )
        self.assertContains(response, "メールアドレスの確認が完了していません")

    def test_required_fields_empty_rejected(self):
        response = self.client.post(reverse("login"), {"login_id": "", "password": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        # ID欄・パスワード欄の両方にメッセージが表示される
        self.assertContains(response, "入力してください", count=2)

    def test_unknown_login_id_same_error_as_wrong_password(self):
        response = self.client.post(
            reverse("login"), {"login_id": "nobody-here", "password": "pass1234"}
        )
        self.assertContains(response, "IDまたはパスワードが違います")
