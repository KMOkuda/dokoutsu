"""2a 回答投稿画面: 投稿頻度の制限と1問題1回答のテスト(docs/test/2a_回答投稿画面.md 8・9章)"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import AnswerPost, Problem, Rank

User = get_user_model()


class AnswerPostLimitTests(TestCase):
    LIMIT_MESSAGE = "短時間に多くの回答が投稿されたため、受け付けられませんでした。時間をおいてもう一度お試しください"

    def setUp(self):
        author = User.objects.create_user(username="lim", email="lim@example.com", password="pass1234")
        self.rank = Rank.objects.first()
        self.problems = [
            Problem.objects.create(
                author=author, title=f"頻度{i}", board_sgf="AB[pd]", turn=Problem.BLACK,
                deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
            )
            for i in range(2)
        ]

    def _post(self, problem, **meta):
        # 同じブラウザからは1問題1回しか回答できないため、同じIPアドレスの別々のブラウザからの投稿として送る
        return self.client_class().post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "連投", "rank": self.rank.pk, "move": "qf", "body": ""},
            **meta,
        )

    def test_11th_post_within_10_minutes_rejected(self):
        for _ in range(10):
            self.assertContains(self._post(self.problems[0]), "投稿しました")
        response = self._post(self.problems[0])
        self.assertContains(response, self.LIMIT_MESSAGE)
        self.assertEqual(AnswerPost.objects.filter(problem=self.problems[0]).count(), 10)

    def test_limit_is_per_problem_and_per_ip(self):
        for _ in range(10):
            self._post(self.problems[0])
        # 別の問題、別のIPアドレスからは投稿できる
        self.assertContains(self._post(self.problems[1]), "投稿しました")
        self.assertContains(self._post(self.problems[0], REMOTE_ADDR="192.0.2.10"), "投稿しました")

    def test_limit_resets_after_10_minutes(self):
        from ..models import AnswerPostLog

        for _ in range(10):
            self._post(self.problems[0])
        AnswerPostLog.objects.update(created_at=timezone.now() - timedelta(minutes=10, seconds=1))
        self.assertContains(self._post(self.problems[0]), "投稿しました")
        # 10分より古い記録(IPアドレス)は数える際に削除され、残らない
        self.assertEqual(AnswerPostLog.objects.count(), 1)

    def test_invalid_posts_are_not_counted(self):
        from ..models import AnswerPostLog

        self.client.post(
            reverse("answer_create", kwargs={"pk": self.problems[0].pk}),
            {"nickname": "", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertEqual(AnswerPostLog.objects.count(), 0)

    def test_railway_uses_leftmost_forwarded_for(self):
        from django.test import RequestFactory, override_settings

        from ..services import client_ip

        request = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="203.0.113.5, 10.0.0.1", REMOTE_ADDR="10.0.0.2")
        with override_settings(IS_RAILWAY=True):
            self.assertEqual(client_ip(request), "203.0.113.5")
        with override_settings(IS_RAILWAY=False):
            self.assertEqual(client_ip(request), "10.0.0.2")

    def test_problem_delete_removes_logs(self):
        from ..models import AnswerPostLog

        self._post(self.problems[0])
        self.problems[0].delete()
        self.assertEqual(AnswerPostLog.objects.count(), 0)

class OneAnswerPerBrowserTests(TestCase):
    def setUp(self):
        author = User.objects.create_user(username="one", email="one@example.com", password="pass1234")
        self.rank = Rank.objects.first()
        self.problem = self._problem(author, Problem.AFTER_DEADLINE, timedelta(days=1))
        self.author = author

    def _problem(self, author, disclosure_type, delta):
        return Problem.objects.create(
            author=author, title="1回答", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + delta, disclosure_type=disclosure_type,
        )

    def _post(self, client, problem, move="qf"):
        return client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "いちど", "rank": self.rank.pk, "move": move, "body": "最初の一手"},
        )

    def test_revisit_shows_own_answer_instead_of_form(self):
        self.assertContains(self._post(self.client, self.problem), "投稿しました！")
        response = self.client.get(reverse("answer_create", kwargs={"pk": self.problem.pk}))
        self.assertContains(response, "回答済みです")
        self.assertContains(response, 'value="いちど"')
        self.assertContains(response, 'data-move="qf"')
        self.assertContains(response, 'value="最初の一手"')
        self.assertNotContains(response, 'id="answer-form"')

    def test_second_post_from_same_browser_rejected(self):
        self._post(self.client, self.problem)
        response = self._post(self.client, self.problem, move="dd")
        self.assertContains(response, "この問題には回答済みです")
        self.assertContains(response, 'data-move="qf"')
        self.assertEqual(AnswerPost.objects.count(), 1)

    def test_other_browser_can_answer(self):
        self._post(self.client, self.problem)
        self.assertContains(self._post(self.client_class(), self.problem, move="dd"), "投稿しました！")
        self.assertEqual(AnswerPost.objects.count(), 2)

    def test_after_answer_type_shows_answer_list_link_on_revisit(self):
        problem = self._problem(self.author, Problem.AFTER_ANSWER, timedelta(days=1))
        self._post(self.client, problem)
        response = self.client.get(reverse("answer_create", kwargs={"pk": problem.pk}))
        self.assertContains(response, reverse("answer_list", kwargs={"pk": problem.pk}))

    def test_after_deadline_type_hides_link_until_closed(self):
        self._post(self.client, self.problem)
        response = self.client.get(reverse("answer_create", kwargs={"pk": self.problem.pk}))
        self.assertNotContains(response, reverse("answer_list", kwargs={"pk": self.problem.pk}))
        self.assertContains(response, "みんなの回答は締切後に公開されます。")
        # 受付終了後に開き直すと、自分の回答とみんなの回答を見るボタンを表示する
        Problem.objects.filter(pk=self.problem.pk).update(closed_at=timezone.now())
        response = self.client.get(reverse("answer_create", kwargs={"pk": self.problem.pk}))
        self.assertContains(response, "締切を過ぎました")
        self.assertContains(response, "回答済みです")
        self.assertContains(response, reverse("answer_list", kwargs={"pk": self.problem.pk}))

    def test_session_without_answer_id_still_treated_as_answered(self):
        # この機能を入れる前のセッション(回答済みの問題の一覧だけを持つ)でも、回答済みとして扱う
        session = self.client.session
        session["answered_problems"] = [str(self.problem.pk)]
        session.save()
        response = self.client.get(reverse("answer_create", kwargs={"pk": self.problem.pk}))
        self.assertContains(response, "回答済みです")
        self.assertNotContains(response, 'id="answer-form"')
