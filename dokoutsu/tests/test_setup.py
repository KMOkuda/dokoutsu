"""棋力の初期データとトップページのテスト"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ..models import Rank

User = get_user_model()


class RankSeedTests(TestCase):
    """共通: 棋力の初期データ"""

    def test_kyu_then_dan_order(self):
        """共通 C3: 棋力の初期データがテーブル定義書2.4のとおり23件そろっている(並び順・区分・表示名)"""
        # テーブル定義書「2.4 dokoutsu_rank」の初期データ: 1〜15はkyuで1級〜15級、16〜23はdanで初段〜8段
        expected = [(n, "kyu", f"{n}級") for n in range(1, 16)]
        expected += [(16, "dan", "初段")] + [(15 + n, "dan", f"{n}段") for n in range(2, 9)]
        actual = list(Rank.objects.order_by("sort_order").values_list("sort_order", "category", "label"))
        self.assertEqual(actual, expected)


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
