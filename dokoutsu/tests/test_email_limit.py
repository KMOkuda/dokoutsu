"""メール送信回数の制限のテスト(基本設計書「3.2 メール送信回数の制限」、docs/test/3a・6a)"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone


User = get_user_model()


class EmailSendLimitTests(TestCase):
    LIMIT_MESSAGE = "送信回数の上限に達しました。時間をおいてもう一度お試しください"

    def _signup(self, username):
        return self.client.post(
            reverse("signup"),
            {"email": "limit@example.com", "username": username, "password": "pass1234"},
        )

    def test_signup_and_resend_share_limit_of_5_per_24_hours(self):
        from django.core import mail

        # 登録1回 + 再送3回 + 再登録1回 = 5回までは送れる
        self._signup("limit1")
        for _ in range(3):
            self.client.post(reverse("signup_sent"))
        self._signup("limit2")
        self.assertEqual(len(mail.outbox), 5)

        # 6回目の再送・再登録は送らず、メッセージを表示する。再登録ではアカウントも置き換えない
        response = self.client.post(reverse("signup_sent"))
        self.assertContains(response, self.LIMIT_MESSAGE)
        response = self._signup("limit3")
        self.assertContains(response, self.LIMIT_MESSAGE)
        self.assertEqual(len(mail.outbox), 5)
        self.assertEqual(list(User.objects.values_list("username", flat=True)), ["limit2"])

    def test_limit_resets_after_24_hours(self):
        from ..models import EmailSendLog

        for _ in range(5):
            EmailSendLog.objects.create(email="limit@example.com", purpose=EmailSendLog.SIGNUP)
        self.assertContains(self._signup("old1"), self.LIMIT_MESSAGE)
        EmailSendLog.objects.update(created_at=timezone.now() - timedelta(hours=24, minutes=1))
        self.assertRedirects(self._signup("new1"), reverse("signup_sent"))
        # 24時間より古い記録は数える際に削除される
        self.assertEqual(EmailSendLog.objects.count(), 1)

    def test_uppercase_address_counted_as_same_address(self):
        from ..models import EmailSendLog

        for _ in range(5):
            EmailSendLog.objects.create(email="limit@example.com", purpose=EmailSendLog.SIGNUP)
        response = self.client.post(
            reverse("signup"),
            {"email": "LIMIT@Example.com", "username": "upper1", "password": "pass1234"},
        )
        self.assertContains(response, self.LIMIT_MESSAGE)

    def test_signup_and_password_reset_counted_separately(self):
        from ..models import EmailSendLog

        User.objects.create_user(username="sep", email="limit@example.com", password="pass1234")
        for _ in range(5):
            EmailSendLog.objects.create(email="limit@example.com", purpose=EmailSendLog.SIGNUP)
        response = self.client.post(reverse("password_reset"), {"email": "limit@example.com"})
        self.assertRedirects(response, reverse("password_reset"))

    def test_password_reset_limit_same_for_registered_and_unregistered(self):
        from django.core import mail

        User.objects.create_user(username="reg", email="reg@example.com", password="pass1234")
        for email in ("reg@example.com", "nobody@example.com"):
            with self.subTest(email=email):
                client = self.client_class()
                for _ in range(5):
                    response = client.post(reverse("password_reset"), {"email": email})
                    self.assertRedirects(response, reverse("password_reset"))
                response = client.post(reverse("password_reset"), {"email": email})
                self.assertContains(response, self.LIMIT_MESSAGE)
        # 実際に送られたのは登録のあるメールアドレスへの5通だけ
        self.assertEqual(len(mail.outbox), 5)
