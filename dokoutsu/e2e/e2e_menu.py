"""E2Eテスト: 共通メニューの開閉(E5)"""

from django.contrib.auth import get_user_model

from .base import E2ETestCase

User = get_user_model()


class MenuFlowTests(E2ETestCase):
    """共通メニューのフロー(E5 開閉)"""

    def test_menu_toggle_flow(self):
        """E5: 共通メニューの開閉(docs/test/e2e_flows.md の手順とスクリーンショット E5_*)"""
        User.objects.create_user(
            username="e2emenu", email="menu@example.com",
            password="pass1234", is_active=True,
        )
        page = self.page
        page.goto(self._url("/login"))
        page.fill("#id_login_id", "e2emenu")
        page.fill("#id_password", "pass1234")
        page.click("button:has-text('ログイン')")
        page.wait_for_url("**/problems/active")

        self.assertTrue(page.is_hidden(".menu-list"))
        page.click(".menu-open")
        self.assertTrue(page.is_visible(".menu-list"))
        # メニュー表示中は背後の画面をスクロールさせない
        self.assertEqual(page.eval_on_selector("body", "b => getComputedStyle(b).overflow"), "hidden")
        self._shot("E5_2_menu_open")

        # 暗転部分をクリックしても閉じない。閉じるのは右上の閉じるボタンのみ
        page.mouse.click(10, 400)
        self.assertTrue(page.is_visible(".menu-list"))

        page.click(".menu-close")
        self.assertTrue(page.is_hidden(".menu-list"))
        self.assertEqual(page.eval_on_selector("body", "b => getComputedStyle(b).overflow"), "visible")
