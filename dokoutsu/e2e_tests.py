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
        deadline = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        page.fill("#id_deadline", deadline)
        page.check('input[name="turn"][value="black"]')
        page.check('input[name="disclosure_type"][value="after_answer"]')

        # 盤面エディタで石を1つ配置する(交点のヒット領域をクリック)
        page.wait_for_selector("[data-goban-editor] svg rect")
        page.click("[data-goban-editor] svg rect")
        self._shot("E2_1_board_with_stone")

        page.click("button:has-text('出題する')")
        page.wait_for_url(re.compile(r".*/problems/.+/created"))
        self.assertIn("E2E作成テスト", page.content())
        self._shot("E2_2_problem_created")

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
        page.wait_for_selector("[data-goban-answer] svg rect")
        page.click("[data-goban-answer] svg rect")
        self._shot("E3_1_move_selected")

        page.fill("#id_nickname", "こだぬき")
        page.select_option("#id_rank", label="15級")
        page.click("button:has-text('この一手で投稿する')")
        page.wait_for_selector("text=投稿しました")
        self._shot("E3_2_posted")

        page.click("text=みんなの回答を見る")
        page.wait_for_url(re.compile(r".*/problems/[0-9a-f-]+$"))
        self.assertIn("こだぬき", page.content())
        self._shot("E3_3_answer_list")

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

        page.click("button:has-text('受付を終了する')")
        page.wait_for_url("**/problems/active")
        self.assertNotIn("E4対象問題", page.content())

        page.goto(self._url("/problems/archive"))
        self.assertIn("E4対象問題", page.content())
        self._shot("E4_2_archive_list")

        page.click("button:has-text('削除する')")
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

        page.mouse.click(10, 700)  # メニュー外(画面下部の余白)をクリック
        self.assertTrue(page.is_hidden(".menu-list"))
