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

INVALID_LINK_MESSAGE = "このリンクは無効です。もう一度パスワード再発行の手続きを行ってください"


def assert_invalid_link_page(testcase, response):
    """詳細設計書 6a「5. エラーケース」3: メッセージを表示し、入力フォームを出さず、
    メールアドレスを入力する状態(パスワード再発行画面)へのリンクを表示する"""
    testcase.assertContains(response, INVALID_LINK_MESSAGE)
    testcase.assertNotContains(response, 'name="new_password"')
    testcase.assertContains(response, f'href="{reverse("password_reset")}"')


class PasswordResetTests(TestCase):
    """6a パスワード再発行: 再設定メールの送信と新しいパスワードの設定"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="grace", email="g@example.com", password="oldpass1", is_active=True
        )

    def test_reset_flow(self):
        """6a N1: 登録済みメールアドレスでリセットメールが送信される / 6a N2: 正しいリンクから新しいパスワードを設定できる"""
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
        """3a E1: メール形式不正 / 6a E1: メール形式不正"""
        response = self.client.post(reverse("password_reset"), {"email": "not-an-email"})
        self.assertContains(response, "正しいメールアドレスを入力してください")

    def test_invalid_token_rejected(self):
        """6a E2: トークン無効・期限切れのリンクでは、メッセージと再発行画面へのリンクを表示し、入力フォームを出さない"""
        uidb64, _ = uid_token(self.user)
        url = reverse(
            "password_reset_confirm", kwargs={"uidb64": uidb64, "token": "bad-token"}
        )
        response = self.client.get(url)
        assert_invalid_link_page(self, response)

    def test_weak_new_password_rejected(self):
        """6a E3: パスワード要件未達"""
        uidb64, token = uid_token(self.user)
        url = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
        response = self.client.post(
            url, {"new_password": "onlyletters", "new_password_confirm": "onlyletters"}
        )
        self.assertContains(response, "組み合わせてください")

    def test_password_mismatch_rejected(self):
        """6a E4: パスワード不一致"""
        uidb64, token = uid_token(self.user)
        url = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
        response = self.client.post(
            url, {"new_password": "newpass1", "new_password_confirm": "different1"}
        )
        self.assertContains(response, "パスワードが一致しません")

    def test_unknown_email_does_not_error(self):
        """6a A1: 未登録のメールアドレスでもエラーを表示しない"""
        response = self.client.post(
            reverse("password_reset"), {"email": "nobody@example.com"}
        )
        self.assertRedirects(response, reverse("password_reset"))

    def test_token_cannot_be_reused(self):
        """6a A2: 一度使用したトークンは再利用できない"""
        uidb64, token = uid_token(self.user)
        url = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
        self.client.post(url, {"new_password": "newpass1", "new_password_confirm": "newpass1"})
        response = self.client.get(url)
        assert_invalid_link_page(self, response)


class PasswordResetInputValidationTests(TestCase):
    """6a パスワード再発行: 入力値の検証とメッセージの表示"""

    def test_empty_email_shows_required_message(self):
        """6a V1: メールアドレス未入力"""
        response = self.client.post(reverse("password_reset"), {"email": ""})
        self.assertContains(response, "入力してください")

    def test_short_new_password_shows_design_message(self):
        """6a V2: 新しいパスワードが8文字未満"""
        user = User.objects.create_user(username="rs", email="rs@example.com", password="pass1234")
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        response = self.client.post(
            reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}),
            {"new_password": "ab1", "new_password_confirm": "ab1"},
        )
        self.assertContains(response, "8文字以上、英字と数字を組み合わせてください")

    def test_empty_new_passwords_show_required_message(self):
        """6a V3: 新しいパスワード・確認用が未入力(詳細設計書 6a「5. エラーケース」6)"""
        user = User.objects.create_user(username="rs2", email="rs2@example.com", password="pass1234")
        uidb64, token = uid_token(user)
        response = self.client.post(
            reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}),
            {"new_password": "", "new_password_confirm": ""},
        )
        # 2項目それぞれの入力欄に表示し、パスワードは変更しない
        self.assertContains(response, "入力してください", count=2)
        user.refresh_from_db()
        self.assertTrue(user.check_password("pass1234"))


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
        # パスワード再発行トークンは生成器の現在時刻(_now)と比べて判定されるため、時刻を進めた状態を作る
        with mock.patch.object(PasswordResetTokenGenerator, "_now", return_value=later):
            return self.client.get(self.path)

    def test_valid_within_60_minutes(self):
        """6a K1: 再設定リンクは60分以内なら有効"""
        response = self._get_after(59)
        self.assertContains(response, "新しいパスワード")
        self.assertNotContains(response, INVALID_LINK_MESSAGE)

    def test_invalid_after_60_minutes(self):
        """6a K2: 再設定リンクは60分を過ぎると無効"""
        response = self._get_after(61)
        assert_invalid_link_page(self, response)
