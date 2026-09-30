"""E2Eテスト: 回答の投稿と回答一覧(E3)"""

import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import Problem, Rank
from .base import E2ETestCase

User = get_user_model()


class AnswerFlowTests(E2ETestCase):
    """回答のフロー(E3 回答の投稿→回答一覧)"""

    def test_answer_and_view_list_flow(self):
        """E3: 回答を投稿してから回答一覧を見る(回答後に公開)(docs/test/e2e_flows.md の手順とスクリーンショット E3_*)"""
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
        # rank_labels(): プルダウンに今並んでいる棋力の名前の一覧を、画面から読み取って返す
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

        # 同じブラウザで開き直すと、入力フォームの代わりに「回答済みです」と自分の回答を表示する
        page.goto(self._url(f"/problems/{problem.pk}/answer"))
        page.wait_for_selector("text=回答済みです")
        self.assertEqual(page.query_selector_all("#answer-form"), [])
        self.assertEqual(page.input_value("input[aria-label='ニックネーム']"), "こだぬき")
        self._shot("E3_4b_already_answered")

        page.click("text=みんなの回答を見る")
        page.wait_for_url(re.compile(r".*/problems/[0-9a-f-]+$"))
        self.assertIn("こだぬき", page.content())
        self._shot("E3_5_answer_list")
