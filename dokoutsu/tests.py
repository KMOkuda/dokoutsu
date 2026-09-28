from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import AnswerPost, Problem, Rank

User = get_user_model()


def _uid_token(user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uidb64, token


# --- 3a 新規登録画面 (docs/test/3a_新規登録画面.md) ---


class SignupTests(TestCase):
    def test_signup_creates_inactive_user_and_sends_mail(self):
        response = self.client.post(
            reverse("signup"),
            {"email": "a@example.com", "username": "alice", "password": "pass1234"},
        )
        self.assertRedirects(response, reverse("signup_sent"))
        user = User.objects.get(email="a@example.com")
        self.assertFalse(user.is_active)
        self.assertFalse(user.check_password("plain-not-stored"))
        self.assertEqual(self.client.session.get("signup_email"), "a@example.com")

    def test_activation_link_activates_user(self):
        self.client.post(
            reverse("signup"),
            {"email": "d@example.com", "username": "dave", "password": "pass1234"},
        )
        user = User.objects.get(email="d@example.com")
        uidb64, token = _uid_token(user)
        response = self.client.get(
            reverse("activate", kwargs={"uidb64": uidb64, "token": token})
        )
        self.assertRedirects(response, reverse("login"))
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_resend_activation_email(self):
        self.client.post(
            reverse("signup"),
            {"email": "resend@example.com", "username": "resend", "password": "pass1234"},
        )
        response = self.client.post(reverse("signup_sent"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "resend@example.com")

    def test_invalid_email_format_rejected(self):
        response = self.client.post(
            reverse("signup"),
            {"email": "not-an-email", "username": "someone", "password": "pass1234"},
        )
        self.assertContains(response, "正しいメールアドレスを入力してください")

    def test_duplicate_email_rejected(self):
        User.objects.create_user(username="bob", email="dup@example.com", password="pass1234")
        response = self.client.post(
            reverse("signup"),
            {"email": "dup@example.com", "username": "carol", "password": "pass1234"},
        )
        self.assertContains(response, "既に登録されています")

    def test_invalid_username_format_rejected(self):
        response = self.client.post(
            reverse("signup"),
            {"email": "z@example.com", "username": "not valid!", "password": "pass1234"},
        )
        self.assertContains(response, "半角英数字")

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username="taken", email="taken@example.com", password="pass1234")
        response = self.client.post(
            reverse("signup"),
            {"email": "new@example.com", "username": "taken", "password": "pass1234"},
        )
        self.assertContains(response, "既に使用されています")

    def test_weak_password_rejected(self):
        response = self.client.post(
            reverse("signup"),
            {"email": "weak@example.com", "username": "weakpw", "password": "onlyletters"},
        )
        self.assertContains(response, "組み合わせてください")

    def test_invalid_activation_link_rejected(self):
        user = User.objects.create_user(
            username="target", email="target@example.com", password="pass1234", is_active=False
        )
        uidb64, _ = _uid_token(user)
        response = self.client.get(
            reverse("activate", kwargs={"uidb64": uidb64, "token": "bad-token"})
        )
        self.assertContains(response, "リンクの有効期限が切れています")
        user.refresh_from_db()
        self.assertFalse(user.is_active)


# --- 3b ログイン画面 (docs/test/3b_ログイン画面.md) ---


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="erin", email="e@example.com", password="pass1234", is_active=True
        )

    def test_login_with_username(self):
        response = self.client.post(
            reverse("login"), {"login_id": "erin", "password": "pass1234"}
        )
        self.assertRedirects(response, reverse("active_problems"))

    def test_login_with_email(self):
        response = self.client.post(
            reverse("login"), {"login_id": "e@example.com", "password": "pass1234"}
        )
        self.assertRedirects(response, reverse("active_problems"))

    def test_remember_unchecked_sets_session_expire_at_browser_close(self):
        self.client.post(
            reverse("login"), {"login_id": "erin", "password": "pass1234"}
        )
        self.assertEqual(self.client.session.get_expire_at_browser_close(), True)

    def test_login_wrong_password(self):
        response = self.client.post(
            reverse("login"), {"login_id": "erin", "password": "wrong"}
        )
        self.assertContains(response, "IDまたはパスワードが違います")

    def test_inactive_user_blocked(self):
        User.objects.create_user(
            username="frank", email="f@example.com", password="pass1234", is_active=False
        )
        response = self.client.post(
            reverse("login"), {"login_id": "frank", "password": "pass1234"}
        )
        self.assertContains(response, "メールアドレスの確認が完了していません")

    def test_required_fields_empty_rejected(self):
        response = self.client.post(reverse("login"), {"login_id": "", "password": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_unknown_login_id_same_error_as_wrong_password(self):
        response = self.client.post(
            reverse("login"), {"login_id": "nobody-here", "password": "pass1234"}
        )
        self.assertContains(response, "IDまたはパスワードが違います")


# --- 6a パスワード再発行画面 (docs/test/6a_パスワード再発行画面.md) ---


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="grace", email="g@example.com", password="oldpass1", is_active=True
        )

    def test_reset_flow(self):
        response = self.client.post(reverse("password_reset"), {"email": "g@example.com"})
        self.assertRedirects(response, reverse("password_reset"))

        uidb64, token = _uid_token(self.user)
        url = reverse(
            "password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}
        )
        response = self.client.post(
            url, {"new_password": "newpass1", "new_password_confirm": "newpass1"}
        )
        self.assertContains(response, "変更しました")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass1"))

    def test_invalid_email_format_rejected(self):
        response = self.client.post(reverse("password_reset"), {"email": "not-an-email"})
        self.assertContains(response, "正しいメールアドレスを入力してください")

    def test_invalid_token_rejected(self):
        uidb64, _ = _uid_token(self.user)
        url = reverse(
            "password_reset_confirm", kwargs={"uidb64": uidb64, "token": "bad-token"}
        )
        response = self.client.get(url)
        self.assertContains(response, "このリンクは無効です")

    def test_weak_new_password_rejected(self):
        uidb64, token = _uid_token(self.user)
        url = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
        response = self.client.post(
            url, {"new_password": "onlyletters", "new_password_confirm": "onlyletters"}
        )
        self.assertContains(response, "組み合わせてください")

    def test_password_mismatch_rejected(self):
        uidb64, token = _uid_token(self.user)
        url = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
        response = self.client.post(
            url, {"new_password": "newpass1", "new_password_confirm": "different1"}
        )
        self.assertContains(response, "パスワードが一致しません")

    def test_unknown_email_does_not_error(self):
        response = self.client.post(
            reverse("password_reset"), {"email": "nobody@example.com"}
        )
        self.assertRedirects(response, reverse("password_reset"))

    def test_token_cannot_be_reused(self):
        uidb64, token = _uid_token(self.user)
        url = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
        self.client.post(url, {"new_password": "newpass1", "new_password_confirm": "newpass1"})
        response = self.client.get(url)
        self.assertContains(response, "このリンクは無効です")


# --- 4a 問題投稿画面 (docs/test/4a_問題投稿画面.md) ---


class ProblemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="hana", email="h@example.com", password="pass1234", is_active=True
        )
        self.client.login(username="hana", password="pass1234")

    def test_create_problem_redirects_to_created(self):
        deadline_date = (timezone.localtime() + timedelta(days=1)).date().isoformat()
        response = self.client.post(
            reverse("problem_new"),
            {
                "title": "テスト問題",
                "deadline_date": deadline_date,
                "deadline_hour": 12,
                "deadline_minute": 0,
                "disclosure_type": Problem.AFTER_DEADLINE,
                "turn": Problem.BLACK,
                "board_sgf": "AB[pd]",
            },
        )
        problem = Problem.objects.get(title="テスト問題")
        self.assertRedirects(response, reverse("problem_created", kwargs={"pk": problem.pk}))
        self.assertEqual(problem.author, self.user)

    def test_created_page_shows_problem_details(self):
        problem = Problem.objects.create(
            author=self.user, title="表示確認", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        response = self.client.get(reverse("problem_created", kwargs={"pk": problem.pk}))
        self.assertContains(response, "表示確認")
        self.assertEqual(response.context["answer_count"], 0)

    def test_empty_title_rejected(self):
        deadline_date = (timezone.localtime() + timedelta(days=1)).date().isoformat()
        response = self.client.post(
            reverse("problem_new"),
            {
                "title": "",
                "deadline_date": deadline_date,
                "deadline_hour": 12,
                "deadline_minute": 0,
                "disclosure_type": Problem.AFTER_DEADLINE,
                "turn": Problem.BLACK,
                "board_sgf": "AB[pd]",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 0)

    def test_past_deadline_rejected(self):
        deadline_date = (timezone.localtime() - timedelta(days=1)).date().isoformat()
        response = self.client.post(
            reverse("problem_new"),
            {
                "title": "過去締切",
                "deadline_date": deadline_date,
                "deadline_hour": 12,
                "deadline_minute": 0,
                "disclosure_type": Problem.AFTER_DEADLINE,
                "turn": Problem.BLACK,
                "board_sgf": "AB[pd]",
            },
        )
        self.assertContains(response, "締切は現在より後の日時を指定してください")

    def test_empty_board_rejected(self):
        deadline_date = (timezone.localtime() + timedelta(days=1)).date().isoformat()
        response = self.client.post(
            reverse("problem_new"),
            {
                "title": "盤面なし",
                "deadline_date": deadline_date,
                "deadline_hour": 12,
                "deadline_minute": 0,
                "disclosure_type": Problem.AFTER_DEADLINE,
                "turn": Problem.BLACK,
                "board_sgf": "",
            },
        )
        self.assertContains(response, "盤面に石を配置してください")

    def test_created_page_404_for_unknown_problem(self):
        response = self.client.get(
            reverse("problem_created", kwargs={"pk": "11111111-1111-1111-1111-111111111111"})
        )
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_view_created_page(self):
        problem = Problem.objects.create(
            author=self.user,
            title="他人の問題",
            board_sgf="AB[pd]",
            turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1),
            disclosure_type=Problem.AFTER_DEADLINE,
        )
        User.objects.create_user(username="ivy", email="i@example.com", password="pass1234", is_active=True)
        self.client.login(username="ivy", password="pass1234")
        response = self.client.get(reverse("problem_created", kwargs={"pk": problem.pk}))
        self.assertEqual(response.status_code, 404)

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("problem_new"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('problem_new')}")


# --- 2a 回答投稿画面 (docs/test/2a_回答投稿画面.md) ---


class AnswerCreateTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username="mika", email="m@example.com", password="pass1234", is_active=True
        )
        self.rank = Rank.objects.first()

    def _make_problem(self, disclosure_type, deadline_delta):
        return Problem.objects.create(
            author=self.author,
            title="問題",
            board_sgf="AB[pd]",
            turn=Problem.BLACK,
            deadline=timezone.now() + deadline_delta,
            disclosure_type=disclosure_type,
        )

    def test_after_answer_type_shows_answer_list_link(self):
        problem = self._make_problem(Problem.AFTER_ANSWER, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "n", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertTrue(response.context["show_answer_list_link"])

    def test_after_deadline_type_hides_answer_list_link(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "n", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertFalse(response.context["show_answer_list_link"])

    def test_deadline_passed_shows_message_and_link_on_get(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(seconds=-1))
        response = self.client.get(reverse("answer_create", kwargs={"pk": problem.pk}))
        self.assertContains(response, "締切を過ぎました")
        self.assertContains(response, reverse("answer_list", kwargs={"pk": problem.pk}))

    def test_answer_create_404_for_unknown_problem(self):
        response = self.client.get(
            reverse("answer_create", kwargs={"pk": "11111111-1111-1111-1111-111111111111"})
        )
        self.assertEqual(response.status_code, 404)

    def test_closed_after_deadline_blocks_new_answers(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(seconds=-1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "x", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertEqual(AnswerPost.objects.count(), 0)
        self.assertContains(response, "締切を過ぎました")

    def test_empty_move_rejected(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "x", "rank": self.rank.pk, "move": "", "body": ""},
        )
        self.assertContains(response, "着手を1つ選んでください")

    def test_empty_nickname_rejected(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertEqual(AnswerPost.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_unselected_rank_rejected(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "x", "rank": "", "move": "qf", "body": ""},
        )
        self.assertEqual(AnswerPost.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_anonymous_can_post_answer(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "x", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertEqual(AnswerPost.objects.count(), 1)
        self.assertContains(response, "投稿しました")

    def test_deadline_judged_by_server_time(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(minutes=1))
        future = timezone.now() + timedelta(minutes=5)
        with mock.patch("django.utils.timezone.now", return_value=future):
            response = self.client.post(
                reverse("answer_create", kwargs={"pk": problem.pk}),
                {"nickname": "x", "rank": self.rank.pk, "move": "qf", "body": ""},
            )
        self.assertEqual(AnswerPost.objects.count(), 0)
        self.assertContains(response, "締切を過ぎました")


# --- 2b 回答一覧画面 (docs/test/2b_回答一覧画面.md) ---


class AnswerListVisibilityTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username="jun", email="j@example.com", password="pass1234", is_active=True
        )
        self.rank = Rank.objects.first()

    def _make_problem(self, disclosure_type, deadline_delta):
        return Problem.objects.create(
            author=self.author,
            title="問題",
            board_sgf="AB[pd]",
            turn=Problem.BLACK,
            deadline=timezone.now() + deadline_delta,
            disclosure_type=disclosure_type,
        )

    def test_author_can_always_view(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        self.client.login(username="jun", password="pass1234")
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertTrue(response.context["can_view"])

    def test_public_after_deadline_regardless_of_type(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(seconds=-1))
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertTrue(response.context["can_view"])

    def test_after_answer_type_visible_once_answered_in_session(self):
        problem = self._make_problem(Problem.AFTER_ANSWER, timedelta(days=1))
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertFalse(response.context["can_view"])

        self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "こだぬき", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertTrue(response.context["can_view"])
        self.assertEqual(AnswerPost.objects.count(), 1)

    def test_empty_answer_list_shows_placeholder(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(seconds=-1))
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertContains(response, "まだ回答がありません")

    def test_answer_list_404_for_unknown_problem(self):
        response = self.client.get(
            reverse("answer_list", kwargs={"pk": "11111111-1111-1111-1111-111111111111"})
        )
        self.assertEqual(response.status_code, 404)

    def test_after_deadline_type_hidden_before_deadline_for_stranger(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertFalse(response.context["can_view"])
        self.assertContains(response, "回答は締切後に公開されます")


# --- 2c 受付中の問題一覧 / 2d 受付終了の問題一覧 (docs/test/2c_*.md, 2d_*.md) ---


class ProblemListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ken", email="k@example.com", password="pass1234", is_active=True
        )
        self.client.login(username="ken", password="pass1234")

    def test_active_and_archive_split(self):
        active = Problem.objects.create(
            author=self.user, title="現役", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        archived = Problem.objects.create(
            author=self.user, title="終了", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() - timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        active_resp = self.client.get(reverse("active_problems"))
        archive_resp = self.client.get(reverse("archive_problems"))
        self.assertIn(active, active_resp.context["problems"])
        self.assertNotIn(archived, active_resp.context["problems"])
        self.assertIn(archived, archive_resp.context["problems"])
        self.assertNotIn(active, archive_resp.context["problems"])

    def test_close_and_delete(self):
        problem = Problem.objects.create(
            author=self.user, title="対象", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        self.client.post(reverse("problem_close", kwargs={"pk": problem.pk}))
        problem.refresh_from_db()
        self.assertIsNotNone(problem.closed_at)

        answer = AnswerPost.objects.create(
            problem=problem, nickname="n", rank=Rank.objects.first(), move="qf"
        )
        self.client.post(reverse("problem_delete", kwargs={"pk": problem.pk}), {"next": "archive_problems"})
        self.assertFalse(Problem.objects.filter(pk=problem.pk).exists())
        self.assertFalse(AnswerPost.objects.filter(pk=answer.pk).exists())

    def test_closing_already_closed_problem_is_noop(self):
        problem = Problem.objects.create(
            author=self.user, title="既に終了", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
            closed_at=timezone.now() - timedelta(hours=1),
        )
        original_closed_at = problem.closed_at
        self.client.post(reverse("problem_close", kwargs={"pk": problem.pk}))
        problem.refresh_from_db()
        self.assertEqual(problem.closed_at, original_closed_at)

    def test_cannot_operate_on_others_problem(self):
        other = User.objects.create_user(username="liz", email="l@example.com", password="pass1234", is_active=True)
        problem = Problem.objects.create(
            author=other, title="他人の問題", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        response = self.client.post(reverse("problem_close", kwargs={"pk": problem.pk}))
        self.assertEqual(response.status_code, 404)
        response = self.client.post(reverse("problem_delete", kwargs={"pk": problem.pk}))
        self.assertEqual(response.status_code, 404)

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("active_problems"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('active_problems')}")
        response = self.client.get(reverse("archive_problems"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('archive_problems')}")


# --- M 共通メニュー (docs/test/M_共通メニュー.md) ---


class CommonMenuTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="nao", email="n@example.com", password="pass1234", is_active=True
        )
        self.problem = Problem.objects.create(
            author=self.user, title="問題", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_ANSWER,
        )

    def test_menu_shown_when_logged_in(self):
        self.client.login(username="nao", password="pass1234")
        response = self.client.get(reverse("active_problems"))
        self.assertContains(response, 'aria-label="共通メニュー"')

    def test_menu_shown_on_answer_screens_when_logged_in(self):
        self.client.login(username="nao", password="pass1234")
        response = self.client.get(reverse("answer_create", kwargs={"pk": self.problem.pk}))
        self.assertContains(response, 'aria-label="共通メニュー"')
        response = self.client.get(reverse("answer_list", kwargs={"pk": self.problem.pk}))
        self.assertContains(response, 'aria-label="共通メニュー"')

    def test_menu_hidden_when_anonymous(self):
        response = self.client.get(reverse("answer_create", kwargs={"pk": self.problem.pk}))
        self.assertNotContains(response, 'aria-label="共通メニュー"')

    def test_menu_hidden_on_auth_screens(self):
        # ログイン済みの場合、これらの画面自体を表示せず受付中の問題一覧へリダイレクトする
        # (詳細設計書「6. セキュリティ上の考慮点」)。結果として共通メニューも表示されない。
        self.client.login(username="nao", password="pass1234")
        for name in ("login", "signup", "password_reset"):
            response = self.client.get(reverse(name))
            self.assertRedirects(response, reverse("active_problems"))


# --- 棋力マスタ ---


class RankSeedTests(TestCase):
    def test_kyu_then_dan_order(self):
        labels = list(Rank.objects.order_by("sort_order").values_list("label", flat=True))
        self.assertEqual(labels[0], "1級")
        self.assertEqual(labels[14], "15級")
        self.assertEqual(labels[15], "初段")
        self.assertEqual(labels[-1], "8段")


class HomeRedirectTests(TestCase):
    def test_root_redirects_to_login_when_anonymous(self):
        response = self.client.get("/", follow=True)
        self.assertEqual(response.redirect_chain[0][0], reverse("active_problems"))
        self.assertEqual(response.request["PATH_INFO"], reverse("login"))

    def test_root_redirects_to_active_problems_when_logged_in(self):
        User.objects.create_user(username="top", email="top@example.com", password="pass1234", is_active=True)
        self.client.login(username="top", password="pass1234")
        response = self.client.get("/")
        self.assertRedirects(response, reverse("active_problems"))
