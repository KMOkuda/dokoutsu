"""6a パスワード再発行画面のテスト(docs/test/6a_パスワード再発行画面.md)"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .helpers import uid_token

User = get_user_model()


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="grace", email="g@example.com", password="oldpass1", is_active=True
        )

    def test_reset_flow(self):
        response = self.client.post(reverse("password_reset"), {"email": "g@example.com"})
        self.assertRedirects(response, reverse("password_reset"))

        uidb64, token = uid_token(self.user)
        url = reverse(
            "password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}
        )
        response = self.client.post(
            url, {"new_password": "newpass1", "new_password_confirm": "newpass1"}
        )
        self.assertContains(response, "変更しました")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass1"))

    def test_invalid_email_format_rejected(self):
        response = self.client.post(reverse("password_reset"), {"email": "not-an-email"})
        self.assertContains(response, "正しいメールアドレスを入力してください")

    def test_invalid_token_rejected(self):
        uidb64, _ = uid_token(self.user)
        url = reverse(
            "password_reset_confirm", kwargs={"uidb64": uidb64, "token": "bad-token"}
        )
        response = self.client.get(url)
        self.assertContains(response, "このリンクは無効です")

    def test_weak_new_password_rejected(self):
        uidb64, token = uid_token(self.user)
        url = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
        response = self.client.post(
            url, {"new_password": "onlyletters", "new_password_confirm": "onlyletters"}
        )
        self.assertContains(response, "組み合わせてください")

    def test_password_mismatch_rejected(self):
        uidb64, token = uid_token(self.user)
        url = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
        response = self.client.post(
            url, {"new_password": "newpass1", "new_password_confirm": "different1"}
        )
        self.assertContains(response, "パスワードが一致しません")

    def test_unknown_email_does_not_error(self):
        response = self.client.post(
            reverse("password_reset"), {"email": "nobody@example.com"}
        )
        self.assertRedirects(response, reverse("password_reset"))

    def test_token_cannot_be_reused(self):
        uidb64, token = uid_token(self.user)
        url = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
        self.client.post(url, {"new_password": "newpass1", "new_password_confirm": "newpass1"})
        response = self.client.get(url)
        self.assertContains(response, "このリンクは無効です")

class PasswordResetInputValidationTests(TestCase):
    def test_empty_email_shows_required_message(self):
        response = self.client.post(reverse("password_reset"), {"email": ""})
        self.assertContains(response, "入力してください")

    def test_short_new_password_shows_design_message(self):
        user = User.objects.create_user(username="rs", email="rs@example.com", password="pass1234")
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        response = self.client.post(
            reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}),
            {"new_password": "ab1", "new_password_confirm": "ab1"},
        )
        self.assertContains(response, "8文字以上、英字と数字を組み合わせてください")

class PasswordResetTimeoutTests(TestCase):
    """パスワード再発行リンクの有効期限は60分(詳細設計書 6a、settings.PASSWORD_RESET_TIMEOUT)。"""

    def setUp(self):
        self.user = User.objects.create_user(username="to", email="to@example.com", password="pass1234")
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        self.path = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})

    def _get_after(self, minutes):
        import datetime

        from django.contrib.auth.tokens import PasswordResetTokenGenerator

        later = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        with mock.patch.object(PasswordResetTokenGenerator, "_now", return_value=later):
            return self.client.get(self.path)

    def test_valid_within_60_minutes(self):
        response = self._get_after(59)
        self.assertContains(response, "新しいパスワード")
        self.assertNotContains(response, "このリンクは無効です")

    def test_invalid_after_60_minutes(self):
        response = self._get_after(61)
        self.assertContains(response, "このリンクは無効です")
