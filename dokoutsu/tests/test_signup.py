"""3a 新規登録画面のテスト(docs/test/3a_新規登録画面.md)"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .helpers import activation_path_from_mail

User = get_user_model()


class SignupTests(TestCase):
    def test_signup_creates_inactive_user_and_sends_mail(self):
        response = self.client.post(
            reverse("signup"),
            {"email": "a@example.com", "username": "alice", "password": "pass1234"},
        )
        self.assertRedirects(response, reverse("signup_sent"))
        user = User.objects.get(email="a@example.com")
        self.assertFalse(user.is_active)
        self.assertFalse(user.check_password("plain-not-stored"))
        self.assertEqual(self.client.session.get("signup_email"), "a@example.com")

    def test_activation_link_activates_user(self):
        self.client.post(
            reverse("signup"),
            {"email": "d@example.com", "username": "dave", "password": "pass1234"},
        )
        user = User.objects.get(email="d@example.com")
        response = self.client.get(activation_path_from_mail())
        self.assertRedirects(response, reverse("login"))
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_resend_activation_email(self):
        self.client.post(
            reverse("signup"),
            {"email": "resend@example.com", "username": "resend", "password": "pass1234"},
        )
        response = self.client.post(reverse("signup_sent"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "resend@example.com")

    def test_invalid_email_format_rejected(self):
        response = self.client.post(
            reverse("signup"),
            {"email": "not-an-email", "username": "someone", "password": "pass1234"},
        )
        self.assertContains(response, "正しいメールアドレスを入力してください")

    def test_duplicate_email_rejected(self):
        User.objects.create_user(username="bob", email="dup@example.com", password="pass1234")
        response = self.client.post(
            reverse("signup"),
            {"email": "dup@example.com", "username": "carol", "password": "pass1234"},
        )
        self.assertContains(response, "既に登録されています")

    def test_invalid_username_format_rejected(self):
        response = self.client.post(
            reverse("signup"),
            {"email": "z@example.com", "username": "not valid!", "password": "pass1234"},
        )
        self.assertContains(response, "半角英数字")

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username="taken", email="taken@example.com", password="pass1234")
        response = self.client.post(
            reverse("signup"),
            {"email": "new@example.com", "username": "taken", "password": "pass1234"},
        )
        self.assertContains(response, "既に使用されています")

    def test_weak_password_rejected(self):
        response = self.client.post(
            reverse("signup"),
            {"email": "weak@example.com", "username": "weakpw", "password": "onlyletters"},
        )
        self.assertContains(response, "組み合わせてください")

    def test_invalid_activation_link_rejected(self):
        user = User.objects.create_user(
            username="target", email="target@example.com", password="pass1234", is_active=False
        )
        # 他人のユーザーIDに書き換えたトークンは、封印が合わないため受け付けない
        from django.core import signing

        other = User.objects.create_user(
            username="other", email="other@example.com", password="pass1234", is_active=False
        )
        signed_for_other = signing.TimestampSigner(salt="dokoutsu.signup.activation").sign(str(other.pk))
        forged = f"{user.pk}:" + signed_for_other.split(":", 1)[1]
        self.assertNotEqual(user.pk, other.pk)
        for token in ("bad-token", forged):
            with self.subTest(token=token):
                response = self.client.get(reverse("activate", kwargs={"token": token}))
                self.assertContains(response, "リンクの有効期限が切れています")
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_activation_link_valid_within_24_hours(self):
        import time

        self.client.post(
            reverse("signup"),
            {"email": "e24@example.com", "username": "e24", "password": "pass1234"},
        )
        path = activation_path_from_mail()
        with mock.patch("django.core.signing.time.time", return_value=time.time() + 60 * 60 * 24 - 60):
            response = self.client.get(path)
        self.assertRedirects(response, reverse("login"))
        self.assertTrue(User.objects.get(username="e24").is_active)

    def test_activation_link_expires_after_24_hours(self):
        import time

        self.client.post(
            reverse("signup"),
            {"email": "x24@example.com", "username": "x24", "password": "pass1234"},
        )
        path = activation_path_from_mail()
        with mock.patch("django.core.signing.time.time", return_value=time.time() + 60 * 60 * 24 + 60):
            response = self.client.get(path)
        self.assertContains(response, "リンクの有効期限が切れています")
        self.assertFalse(User.objects.get(username="x24").is_active)

class SignupInputValidationTests(TestCase):
    def _post(self, **overrides):
        data = {"email": "v@example.com", "username": "valid1", "password": "pass1234"}
        data.update(overrides)
        return self.client.post(reverse("signup"), data)

    def test_empty_fields_show_required_message(self):
        response = self._post(email="", username="", password="")
        self.assertContains(response, "入力してください", count=3)

    def test_japanese_username_rejected(self):
        response = self._post(username="たろう123")
        self.assertContains(response, "IDは半角英数字で入力してください")
        self.assertFalse(User.objects.exists())

    def test_fullwidth_digit_username_rejected(self):
        response = self._post(username="taro１２３")
        self.assertContains(response, "IDは半角英数字で入力してください")

    def test_short_password_shows_design_message(self):
        response = self._post(password="ab1")
        self.assertContains(response, "8文字以上、英字と数字を組み合わせてください")

    def test_password_with_fullwidth_digit_rejected(self):
        response = self._post(password="abcdefg１")
        self.assertContains(response, "8文字以上、英字と数字を組み合わせてください")

    def test_username_over_150_chars_rejected(self):
        response = self._post(username="a" * 151)
        self.assertContains(response, "150文字以内で入力してください")

    def test_username_150_chars_accepted(self):
        response = self._post(username="a" * 150)
        self.assertRedirects(response, reverse("signup_sent"))
