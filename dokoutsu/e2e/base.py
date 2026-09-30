"""E2Eテストの共通の準備(docs/test/e2e_flows.md)。

実際のブラウザ(Playwright + Chromium)で画面を操作して検証する。
`python3 manage.py test dokoutsu.e2e -p "e2e_*.py"` で実行する。
ファイル名を test_*.py にしないのは、サーバー側のテスト(python3 manage.py test dokoutsu)で
ブラウザが必要なE2Eテストまで実行されないようにするため。
各テストの主要な画面状態のスクリーンショットを docs/test/screenshots/ に保存する。

テストで使うPlaywrightの主な操作:
- page.goto(URL): 画面を開く
- page.fill(セレクタ, 文字): 入力欄に文字を入れる
- page.click(セレクタ): ボタンやリンクを押す
- page.mouse.down() / up(): 指(マウス)を押す / 離す。盤面の「押している間」「離したとき」を再現する
- page.wait_for_url(URL) / wait_for_selector(セレクタ): 画面の移動や表示を待ってから次へ進む
- page.is_disabled / is_visible / is_hidden(セレクタ): ボタンが押せないか、要素が見えているかを確かめる
- self._shot(名前): その時点の画面のスクリーンショットを保存する
- self._submit_and_assert_locked(...): 送信ボタンを押し、押した直後に非活性になることを確かめる
"""

import os
import re

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings

from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "docs", "test", "screenshots",
)
CHROMIUM_PATH = os.environ.get(
    "E2E_CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class E2ETestCase(StaticLiveServerTestCase):
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

    def _submit_and_assert_locked(self, selector, label, also=()):
        """selector(CSSセレクター)のボタンを押し、押した直後(次の画面が表示される前)に、
        そのボタンと also のボタンが非活性になっていることを確かめる(二重送信の防止)。
        label は押したボタンの表示名で、別のボタンを押していないことの確認に使う。次の画面の読み込みまで待つ"""
        selectors = [selector, *also]
        # Playwrightのclickは押した後の状態を待ってしまうため、ブラウザ内で押して、同じ瞬間の状態を読み取る
        with self.page.expect_navigation():
            text, states = self.page.evaluate(
                """(selectors) => {
                    const button = document.querySelector(selectors[0]);
                    button.click();
                    return [button.textContent.trim(), selectors.map((s) => document.querySelector(s).disabled)];
                }""",
                selectors,
            )
        self.assertEqual(text, label)
        for target, disabled in zip(selectors, states):
            self.assertTrue(disabled, f"送信した直後に非活性になっていない: {target}")

    def _url(self, path):
        return f"{self.live_server_url}{path}"

    def _extract_link(self, body):
        match = re.search(r"https?://\S+", body)
        self.assertIsNotNone(match, "メール本文にリンクが見つかりません")
        return match.group(0)
