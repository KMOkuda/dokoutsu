"""E2Eテスト: 問題の作成(E2)、問題一覧での終了・シェア・削除(E4)"""

import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import Problem
from .base import E2ETestCase

User = get_user_model()


class ProblemFlowTests(E2ETestCase):
    """問題の出題と管理のフロー(E2 出題、E4 受付終了・シェア・削除)"""

    def test_create_problem_flow(self):
        """E2: 問題を作成して出題完了画面を見る(docs/test/e2e_flows.md の手順とスクリーンショット E2_*)"""
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
        line_href = page.get_attribute(".share-buttons [data-share='line']", "href")
        self.assertTrue(line_href.startswith("https://line.me/R/msg/text/?"))
        self.assertIn("E2E%E4%BD%9C%E6%88%90%E3%83%86%E3%82%B9%E3%83%88", line_href)  # タイトル(URLエンコード)
    def test_close_and_delete_flow(self):
        """E4: 問題一覧で終了・シェア・削除を操作する(docs/test/e2e_flows.md の手順とスクリーンショット E4_*)"""
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
        # シェアするのは回答投稿画面のURL(リンク先ではURLエンコードされ「/」が「%2F」になる)
        self.assertIn("%2Fanswer", page.get_attribute("#share-sheet [data-share='x']", "href"))
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
