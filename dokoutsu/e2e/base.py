"""E2Eテストの共通の準備(docs/test/e2e_flows.md)。

実際のブラウザ(Playwright + Chromium)で画面を操作して検証する。
`python3 manage.py test dokoutsu.e2e -p "e2e_*.py"` で実行する。
ファイル名を test_*.py にしないのは、サーバー側のテスト(python3 manage.py test dokoutsu)で
ブラウザが必要なE2Eテストまで実行されないようにするため。
各テストの主要な画面状態のスクリーンショットを docs/test/screenshots/ に保存する。
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

    def _url(self, path):
        return f"{self.live_server_url}{path}"

    def _extract_link(self, body):
        match = re.search(r"https?://\S+", body)
        self.assertIsNotNone(match, "メール本文にリンクが見つかりません")
        return match.group(0)
