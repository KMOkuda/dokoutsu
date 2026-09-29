"""E2Eテスト(docs/test/e2e_flows.md 対応)。

実際のブラウザ(Playwright + Chromium)で画面を操作して検証する。
`python3 manage.py test dokoutsu.e2e_tests` で実行する。
各テストの主要な画面状態のスクリーンショットを docs/test/screenshots/ に保存する。
"""

import os
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail
from django.test import override_settings
from django.utils import timezone

from playwright.sync_api import sync_playwright

from .models import Problem, Rank

User = get_user_model()

SCREENSHOT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "test", "screenshots",
)
CHROMIUM_PATH = os.environ.get(
    "E2E_CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class E2EFlowTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(executable_path=CHROMIUM_PATH)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 430, "height": 800})

    def tearDown(self):
        self.page.close()

    def _shot(self, name):
        self.page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"{name}.png"))

    def _url(self, path):
        return f"{self.live_server_url}{path}"

    def _extract_link(self, body):
        match = re.search(r"https?://\S+", body)
        self.assertIsNotNone(match, "メール本文にリンクが見つかりません")
        return match.group(0)

    # --- E1: 新規登録からログインまで ---

    def test_signup_to_login_flow(self):
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
        self._shot("E1_3_active_problems_after_login")

    # --- E2: 問題を作成して出題完了画面を見る ---

    def test_create_problem_flow(self):
        User.objects.create_user(
            username="e2ecreator", email="creator@example.com",
            password="pass1234", is_active=True,
        )
        page = self.page
        page.goto(self._url("/login"))
        page.fill("#id_login_id", "e2ecreator")
        page.fill("#id_password", "pass1234")
        page.click("button:has-text('ログイン')")
        page.wait_for_url("**/problems/active")

        page.goto(self._url("/problems/new"))
        page.fill("#id_title", "E2E作成テスト")
        deadline_date = (timezone.localtime() + timedelta(days=1)).date().isoformat()
        page.fill("#id_deadline_date", deadline_date)
        page.select_option("#id_deadline_hour", "18")
        page.select_option("#id_deadline_minute", "0")
        tomorrow = timezone.localtime() + timedelta(days=1)
        weekday = "月火水木金土日"[tomorrow.weekday()]
        self.assertEqual(
            page.inner_text(".date-display"),
            f"{tomorrow.year}年{tomorrow.month}月{tomorrow.day}日（{weekday}）",
        )
        page.click("label.check-item:has-text('回答後に公開リンクを表示')")
        page.click("label.toggle-item:has-text('黒番')")
        self._shot("E2_1_problem_form")

        # 盤面エディタの中央付近(天元)をタップして黒石を置く
        board = page.wait_for_selector("[data-goban-editor] svg")
        box = board.bounding_box()
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.wait_for_function("document.getElementById('id_board_sgf').value !== ''")
        board.scroll_into_view_if_needed()
        self._shot("E2_2_board_with_stone")

        page.click("#problem-submit")
        page.wait_for_selector("#publish-dialog[open]")
        self.assertIn("E2E作成テスト", page.inner_text("#publish-dialog"))
        self.assertEqual(
            page.inner_text("[data-summary='deadline']"),
            f"{tomorrow.month}月{tomorrow.day}日（{weekday}）18:00",
        )
        self._shot("E2_3_publish_confirm")

        page.click("#publish-confirm")
        page.wait_for_url(re.compile(r".*/problems/.+/created"))
        self.assertIn("E2E作成テスト", page.content())
        self._shot("E2_4_problem_created")

    # --- E3: 回答を投稿してから回答一覧を見る ---

    def test_answer_and_view_list_flow(self):
        author = User.objects.create_user(
            username="e2eauthor", email="author@example.com",
            password="pass1234", is_active=True,
        )
        problem = Problem.objects.create(
            author=author, title="E2E回答テスト", board_sgf="AB[pd]",
            turn=Problem.BLACK, deadline=timezone.now() + timedelta(days=1),
            disclosure_type=Problem.AFTER_ANSWER,
        )
        Rank.objects.first()  # 初期データが投入済みであることの前提確認

        page = self.page
        page.goto(self._url(f"/problems/{problem.pk}/answer"))
        self._shot("E3_1_answer_form")
        # 共有URLを直接開いた場合は戻る先がアプリの外になるため、戻るボタンを表示しない
        self.assertTrue(page.is_hidden(".header-back"))
        self.assertTrue(page.is_disabled("#answer-submit"))

        page.fill("#id_nickname", "こだぬき")
        # 棋力は「級」「段」のタブで選択肢を切り替える。初期表示は級
        rank_labels = lambda: page.eval_on_selector(
            "#id_rank", "s => Array.from(s.options).slice(1).map(o => o.text)"
        )
        self.assertTrue(all(label.endswith("級") for label in rank_labels()))
        page.click(".rank-tabs button:has-text('段')")
        self.assertTrue(all(label.endswith("段") for label in rank_labels()))
        self._shot("E3_1b_rank_dan_tab")
        page.click(".rank-tabs button:has-text('級')")
        page.select_option("#id_rank", label="15級")
        page.fill("#id_body", "天元が急場")

        # 盤面中央(天元)を押して離すと着手が確定し、投稿ボタンが有効になる
        board = page.wait_for_selector("[data-goban-answer] svg")
        box = board.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        self._shot("E3_2_guide_on_press")
        page.mouse.up()
        page.wait_for_function("!document.getElementById('answer-submit').disabled")
        first_move = page.input_value("#id_move")

        # 投稿前なら別の交点を押して選び直せる。最後に選んだ着手が送信される
        cell = box["width"] / 20
        page.mouse.click(box["x"] + box["width"] / 2 + cell * 2, box["y"] + box["height"] / 2)
        self.assertNotEqual(page.input_value("#id_move"), first_move)
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        self.assertEqual(page.input_value("#id_move"), first_move)
        self._shot("E3_3_move_selected")

        page.click("#answer-submit")
        page.wait_for_selector("text=投稿しました")
        self._shot("E3_4_posted")

        page.click("text=みんなの回答を見る")
        page.wait_for_url(re.compile(r".*/problems/[0-9a-f-]+$"))
        self.assertIn("こだぬき", page.content())
        self._shot("E3_5_answer_list")

    # --- E4: 受付中の問題一覧で終了・削除を操作する ---

    def test_close_and_delete_flow(self):
        user = User.objects.create_user(
            username="e2elist", email="list@example.com",
            password="pass1234", is_active=True,
        )
        Problem.objects.create(
            author=user, title="E4対象問題", board_sgf="AB[pd]",
            turn=Problem.BLACK, deadline=timezone.now() + timedelta(days=1),
            disclosure_type=Problem.AFTER_DEADLINE,
        )

        page = self.page
        page.goto(self._url("/login"))
        page.fill("#id_login_id", "e2elist")
        page.fill("#id_password", "pass1234")
        page.click("button:has-text('ログイン')")
        page.wait_for_url("**/problems/active")
        self.assertIn("E4対象問題", page.content())
        self._shot("E4_1_active_list")

        # アプリ内から移動した場合は戻るボタンを表示し、押すと元の画面に戻る
        page.click("a.btn-outline:has-text('問題')")
        page.wait_for_url("**/answer")
        self.assertTrue(page.is_visible(".header-back"))
        page.click(".header-back")
        page.wait_for_url("**/problems/active")

        page.click(".btn-icon[data-sheet-trigger='actions']")
        page.wait_for_selector("#action-sheet[open]")
        self._shot("E4_2_action_sheet")
        page.click("#action-sheet >> text=出題を終了する")
        page.wait_for_selector("#close-dialog[open]")
        self._shot("E4_3_close_confirm")
        page.click("#close-dialog button.confirm-primary")
        page.wait_for_url("**/problems/active")
        self.assertNotIn("E4対象問題", page.content())
        self._shot("E4_4_active_empty")

        page.goto(self._url("/problems/archive"))
        self.assertIn("E4対象問題", page.content())
        self._shot("E4_5_archive_list")

        page.click("[data-sheet-trigger='share']")
        page.wait_for_selector("#share-sheet[open]")
        self._shot("E4_6_share_sheet")
        page.click("#share-sheet >> text=キャンセル")

        page.click(".btn-icon[data-sheet-trigger='actions']")
        page.wait_for_selector("#action-sheet[open]")
        page.click("#action-sheet >> text=問題を削除する")
        page.wait_for_selector("#delete-dialog[open]")
        self._shot("E4_7_delete_confirm")
        page.click("#delete-dialog button.confirm-danger")
        page.wait_for_url("**/problems/archive")
        self.assertNotIn("E4対象問題", page.content())

    # --- E5: 共通メニューの開閉 ---

    def test_menu_toggle_flow(self):
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
        self._shot("E5_1_menu_open")

        # 暗転部分をクリックしても閉じない。閉じるのは右上の閉じるボタンのみ
        page.mouse.click(10, 400)
        self.assertTrue(page.is_visible(".menu-list"))

        page.click(".menu-close")
        self.assertTrue(page.is_hidden(".menu-list"))
        self.assertEqual(page.eval_on_selector("body", "b => getComputedStyle(b).overflow"), "visible")

    # --- E6: 送信ボタンの活性条件と入力エラーの表示 ---

    def test_input_errors_displayed_flow(self):
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
        page.click("button:has-text('ログイン')")
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

    # --- E7: パスワード再発行(送信ボタンの活性条件を含む) ---

    def test_password_reset_flow(self):
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
