"""3a 新規登録画面: 未確認アカウントへの再登録のテスト(docs/test/3a_新規登録画面.md 8章)"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .helpers import activation_path_from_mail

User = get_user_model()


class ReRegistrationTests(TestCase):
    """確認リンクを開かなかった(未確認の)アカウントは、同じメールアドレス・IDで登録し直せる(詳細設計書 3a)。"""

    def _signup(self, email="re@example.com", username="rereg", password="pass1234"):
        return self.client.post(
            reverse("signup"), {"email": email, "username": username, "password": password}
        )

    def test_same_email_and_id_can_register_again_while_unverified(self):
        """3a R1: 未確認のまま同じメールアドレス・IDで登録し直す"""
        self._signup(password="first123")
        old_path = activation_path_from_mail()
        old_pk = User.objects.get(username="rereg").pk

        response = self._signup(password="second123")
        self.assertRedirects(response, reverse("signup_sent"))
        user = User.objects.get(username="rereg")
        self.assertNotEqual(user.pk, old_pk)
        self.assertEqual(User.objects.filter(email="re@example.com").count(), 1)
        self.assertTrue(user.check_password("second123"))

        # 前の確認リンクは使えず、新しいリンクで有効化できる
        self.assertContains(self.client.get(old_path), "リンクの有効期限が切れています")
        self.assertRedirects(self.client.get(activation_path_from_mail()), reverse("login"))

    def test_unverified_account_replaced_when_either_email_or_id_matches(self):
        """3a R2: メールアドレスとIDがそれぞれ別の未確認アカウントと一致"""
        self._signup(email="a1@example.com", username="alpha1")
        self._signup(email="b1@example.com", username="beta1")
        # メールアドレスはalpha1の、IDはbeta1のものを使って登録し直すと、両方の未確認アカウントが置き換わる
        response = self._signup(email="a1@example.com", username="beta1")
        self.assertRedirects(response, reverse("signup_sent"))
        self.assertEqual(list(User.objects.values_list("username", "email")), [("beta1", "a1@example.com")])

    def test_verified_account_still_blocks_duplicates(self):
        """3a R3: 確認済みアカウントとの重複は従来どおり拒否"""
        User.objects.create_user(username="taken2", email="taken2@example.com", password="pass1234", is_active=True)
        response = self._signup(email="taken2@example.com", username="other2")
        self.assertContains(response, "このメールアドレスは既に登録されています")
        response = self._signup(email="new2@example.com", username="taken2")
        self.assertContains(response, "このIDは既に使用されています")

    def test_expired_link_page_guides_to_signup(self):
        """3a R4: 期限切れ・無効リンクで再登録を案内"""
        response = self.client.get(reverse("activate", kwargs={"token": "bad-token"}))
        self.assertContains(response, "もう一度新規登録を行ってください")
        self.assertContains(response, f'href="{reverse("signup")}"')
