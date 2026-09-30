"""棋力の初期データとトップページのテスト"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ..models import Rank

User = get_user_model()


class RankSeedTests(TestCase):
    """共通: 棋力の初期データ"""

    def test_kyu_then_dan_order(self):
        """共通 C3: 棋力の初期データの並び順"""
        labels = list(Rank.objects.order_by("sort_order").values_list("label", flat=True))
        self.assertEqual(labels[0], "1級")
        self.assertEqual(labels[14], "15級")
        self.assertEqual(labels[15], "初段")
        self.assertEqual(labels[-1], "8段")


class HomeRedirectTests(TestCase):
    """共通: トップページ(/)のリダイレクト"""

    def test_root_redirects_to_login_when_anonymous(self):
        """共通 C1: 未ログインでトップページを開く"""
        response = self.client.get("/", follow=True)
        self.assertEqual(response.redirect_chain[0][0], reverse("active_problems"))
        self.assertEqual(response.request["PATH_INFO"], reverse("login"))

    def test_root_redirects_to_active_problems_when_logged_in(self):
        """共通 C2: ログイン済みでトップページを開く"""
        User.objects.create_user(username="top", email="top@example.com", password="pass1234", is_active=True)
        self.client.login(username="top", password="pass1234")
        response = self.client.get("/")
        self.assertRedirects(response, reverse("active_problems"))
