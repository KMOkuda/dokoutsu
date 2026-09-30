"""3a 新規登録画面: 入力値の検証のテスト(docs/test/3a_新規登録画面.md 6章)"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class SignupInputValidationTests(TestCase):
    """3a 新規登録: 入力値の検証(必須・文字の種類・文字数)とメッセージの表示"""

    def _post(self, **overrides):
        data = {"email": "v@example.com", "username": "valid1", "password": "pass1234"}
        data.update(overrides)
        return self.client.post(reverse("signup"), data)

    def test_empty_fields_show_required_message(self):
        """3a V1: 3項目とも未入力"""
        response = self._post(email="", username="", password="")
        self.assertContains(response, "入力してください", count=3)

    def test_japanese_username_rejected(self):
        """3a V2: IDに日本語"""
        response = self._post(username="たろう123")
        self.assertContains(response, "IDは半角英数字で入力してください")
        self.assertFalse(User.objects.exists())

    def test_fullwidth_digit_username_rejected(self):
        """3a V3: IDに全角数字"""
        response = self._post(username="taro１２３")
        self.assertContains(response, "IDは半角英数字で入力してください")

    def test_short_password_shows_design_message(self):
        """3a V4: パスワードが8文字未満"""
        response = self._post(password="ab1")
        self.assertContains(response, "8文字以上、英字と数字を組み合わせてください")

    def test_password_with_fullwidth_digit_rejected(self):
        """3a V5: パスワードの数字が全角"""
        response = self._post(password="abcdefg１")
        self.assertContains(response, "8文字以上、英字と数字を組み合わせてください")

    def test_username_over_150_chars_rejected(self):
        """3a V6: IDが上限超過"""
        response = self._post(username="a" * 151)
        self.assertContains(response, "150文字以内で入力してください")

    def test_username_150_chars_accepted(self):
        """3a V7: IDが上限ちょうど"""
        response = self._post(username="a" * 150)
        self.assertRedirects(response, reverse("signup_sent"))

    def test_email_over_254_chars_rejected(self):
        """3a V8: メールアドレスが上限(254文字)を超える"""
        response = self._post(email="a@" + "b" * 249 + ".com")  # 255文字
        self.assertContains(response, "254文字以内で入力してください")
        self.assertFalse(User.objects.exists())

    def test_password_over_128_chars_rejected(self):
        """3a V9: パスワードが上限(128文字)を超える"""
        response = self._post(password="a1" * 64 + "b")  # 129文字
        self.assertContains(response, "128文字以内で入力してください")
        self.assertFalse(User.objects.exists())
