"""E2Eテスト: 新規登録からログインまで(E1)、送信ボタンの活性条件と入力エラーの表示(E6)、パスワード再発行(E7)"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone

from .base import E2ETestCase

User = get_user_model()


class AuthFlowTests(E2ETestCase):
    """アカウント関係のフロー(E1 新規登録→ログイン、E6 ボタンの活性条件と入力エラー、E7 パスワード再発行)"""

    def test_signup_to_login_flow(self):
        """E1: 新規登録からログインまで(docs/test/e2e_flows.md の手順とスクリーンショット E1_*)"""
        page = self.page
        page.goto(self._url("/signup"))
        self._shot("E1_1_signup_form")

        page.fill("#id_email", "e2e-signup@example.com")
        page.fill("#id_username", "e2esignup")
        page.fill("#id_password", "pass1234")
        page.click("button:has-text('登録する')")
        page.wait_for_url("**/signup/sent")
        self.assertIn("e2e-signup@example.com", page.content())
        self._shot("E1_2_signup_sent")

        self.assertEqual(len(mail.outbox), 1)
        link = self._extract_link(mail.outbox[0].body)
        page.goto(link)
        page.wait_for_url("**/login")

        page.fill("#id_login_id", "e2esignup")
        page.fill("#id_password", "pass1234")
        page.click("button:has-text('ログイン')")
        page.wait_for_url("**/problems/active")
        self.assertIn('aria-label="共通メニュー"', page.content())
        self._shot("E1_4_active_problems_after_login")
    def test_input_errors_displayed_flow(self):
        """E6: 送信ボタンの活性条件と入力エラーの表示(docs/test/e2e_flows.md の手順とスクリーンショット E6_*)"""
        User.objects.create_user(
            username="e2eerror", email="error@example.com",
            password="pass1234", is_active=True,
        )
        page = self.page

        # 必須項目がそろうまでログインボタンは押せない
        page.goto(self._url("/login"))
        self.assertTrue(page.is_disabled("button:has-text('ログイン')"))
        page.fill("#id_login_id", "e2eerror")
        self.assertTrue(page.is_disabled("button:has-text('ログイン')"))
        page.fill("#id_password", "wrongpass1")
        self.assertTrue(page.is_enabled("button:has-text('ログイン')"))
        # 送信した瞬間(次の画面が表示される前)にボタンが押せなくなることを確かめる(二重送信の防止)。
        # requestSubmit(): ボタンを押したときと同じようにフォームを送信する
        disabled_right_after_submit = page.evaluate(
            """() => {
                const button = document.querySelector("button[type='submit']");
                button.form.requestSubmit(button);
                return button.disabled;
            }"""
        )
        self.assertTrue(disabled_right_after_submit)
        page.wait_for_selector(".errorlist")
        self.assertIn("IDまたはパスワードが違います", page.inner_text("form"))
        self._shot("E6_1_login_error")

        page.goto(self._url("/signup"))
        self.assertTrue(page.is_disabled("button:has-text('登録する')"))
        page.fill("#id_email", "not-an-email")
        page.fill("#id_username", "たろう")
        page.fill("#id_password", "ab1")
        page.click("button:has-text('登録する')")
        page.wait_for_selector(".errorlist")
        errors = page.inner_text("form")
        self.assertIn("正しいメールアドレスを入力してください", errors)
        self.assertIn("IDは半角英数字で入力してください", errors)
        self.assertIn("8文字以上、英字と数字を組み合わせてください", errors)
        self._shot("E6_2_signup_invalid")

        page.goto(self._url("/login"))
        page.fill("#id_login_id", "e2eerror")
        page.fill("#id_password", "pass1234")
        page.click("button:has-text('ログイン')")
        page.wait_for_url("**/problems/active")

        # 問題投稿: 締切は初期値が入っている。タイトルと盤面がそろうまで出題ボタンは押せない
        page.goto(self._url("/problems/new"))
        self.assertTrue(page.is_disabled("#problem-submit"))
        page.fill("#id_title", "締切エラー確認")
        self.assertTrue(page.is_disabled("#problem-submit"))
        board = page.wait_for_selector("[data-goban-editor] svg")
        box = board.bounding_box()
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        self.assertTrue(page.is_enabled("#problem-submit"))

        # 過去の締切はサーバー側の入力チェックでエラーになり、画面に表示される
        yesterday = (timezone.localtime() - timedelta(days=1)).date().isoformat()
        page.fill("#id_deadline_date", yesterday)
        page.click("#problem-submit")
        page.click("#publish-confirm")
        page.wait_for_selector(".errorlist")
        self.assertIn("締切は現在より後の日時を指定してください", page.inner_text("#problem-form"))
        self._shot("E6_3_problem_past_deadline")
    def test_password_reset_flow(self):
        """E7: パスワード再発行(docs/test/e2e_flows.md の手順とスクリーンショット E7_*)"""
        User.objects.create_user(
            username="e2ereset", email="reset@example.com",
            password="oldpass123", is_active=True,
        )
        page = self.page

        page.goto(self._url("/password_reset"))
        self.assertTrue(page.is_disabled("button:has-text('再設定リンクを送る')"))
        page.fill("#id_email", "reset@example.com")
        self.assertTrue(page.is_enabled("button:has-text('再設定リンクを送る')"))
        page.click("button:has-text('再設定リンクを送る')")
        page.wait_for_selector("text=メールを送りました")
        self._shot("E7_1_reset_sent")

        self.assertEqual(len(mail.outbox), 1)
        page.goto(self._extract_link(mail.outbox[0].body))
        submit = "button:has-text('パスワードを変更する')"
        self.assertTrue(page.is_disabled(submit))
        page.fill("#id_new_password", "newpass123")
        self.assertTrue(page.is_disabled(submit))
        page.fill("#id_new_password_confirm", "newpass123")
        self.assertTrue(page.is_enabled(submit))
        self._shot("E7_2_new_password_form")
        page.click(submit)
        page.wait_for_selector("text=変更しました")
        self._shot("E7_3_changed")

        page.click("text=ログインする")
        page.wait_for_url("**/login")
        page.fill("#id_login_id", "e2ereset")
        page.fill("#id_password", "newpass123")
        page.click("button:has-text('ログイン')")
        page.wait_for_url("**/problems/active")
