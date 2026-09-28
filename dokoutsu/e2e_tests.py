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
        self.assertTrue(page.is_disabled("#answer-submit"))

        page.fill("#id_nickname", "こだぬき")
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
        self._shot("E5_1_menu_open")

        page.mouse.click(10, 400)  # ドロワー外の暗転部分をクリック
        self.assertTrue(page.is_hidden(".menu-list"))

        page.click(".menu-open")
        page.click(".menu-close")
        self.assertTrue(page.is_hidden(".menu-list"))
