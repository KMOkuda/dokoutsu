from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import AnswerPost, Problem, Rank

User = get_user_model()


class SignupTests(TestCase):
    def test_signup_creates_inactive_user_and_sends_mail(self):
        response = self.client.post(
            reverse("signup"),
            {"email": "a@example.com", "username": "alice", "password": "pass1234"},
        )
        self.assertRedirects(response, reverse("signup_sent"))
        user = User.objects.get(email="a@example.com")
        self.assertFalse(user.is_active)
        self.assertEqual(self.client.session.get("signup_email"), "a@example.com")

    def test_duplicate_email_rejected(self):
        User.objects.create_user(username="bob", email="dup@example.com", password="pass1234")
        response = self.client.post(
            reverse("signup"),
            {"email": "dup@example.com", "username": "carol", "password": "pass1234"},
        )
        self.assertContains(response, "既に登録されています")

    def test_activation_link_activates_user(self):
        self.client.post(
            reverse("signup"),
            {"email": "d@example.com", "username": "dave", "password": "pass1234"},
        )
        user = User.objects.get(email="d@example.com")
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        response = self.client.get(
            reverse("activate", kwargs={"uidb64": uidb64, "token": token})
        )
        self.assertRedirects(response, reverse("login"))
        user.refresh_from_db()
        self.assertTrue(user.is_active)


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


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="grace", email="g@example.com", password="oldpass1", is_active=True
        )

    def test_reset_flow(self):
        response = self.client.post(reverse("password_reset"), {"email": "g@example.com"})
        self.assertRedirects(response, reverse("password_reset"))

        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        url = reverse(
            "password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}
        )
        response = self.client.post(
            url, {"new_password": "newpass1", "new_password_confirm": "newpass1"}
        )
        self.assertContains(response, "変更しました")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass1"))

    def test_unknown_email_does_not_error(self):
        response = self.client.post(
            reverse("password_reset"), {"email": "nobody@example.com"}
        )
        self.assertRedirects(response, reverse("password_reset"))


class ProblemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="hana", email="h@example.com", password="pass1234", is_active=True
        )
        self.client.login(username="hana", password="pass1234")

    def test_create_problem_redirects_to_created(self):
        deadline = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        response = self.client.post(
            reverse("problem_new"),
            {
                "title": "テスト問題",
                "deadline": deadline,
                "disclosure_type": Problem.AFTER_DEADLINE,
                "turn": Problem.BLACK,
                "board_sgf": "AB[pd]",
            },
        )
        problem = Problem.objects.get(title="テスト問題")
        self.assertRedirects(response, reverse("problem_created", kwargs={"pk": problem.pk}))
        self.assertEqual(problem.author, self.user)

    def test_past_deadline_rejected(self):
        deadline = (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        response = self.client.post(
            reverse("problem_new"),
            {
                "title": "過去締切",
                "deadline": deadline,
                "disclosure_type": Problem.AFTER_DEADLINE,
                "turn": Problem.BLACK,
                "board_sgf": "AB[pd]",
            },
        )
        self.assertContains(response, "締切は現在より後の日時を指定してください")

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


class AnswerVisibilityTests(TestCase):
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

    def test_after_deadline_type_hidden_before_deadline_for_stranger(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertFalse(response.context["can_view"])

    def test_public_after_deadline_regardless_of_type(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(seconds=-1))
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertTrue(response.context["can_view"])

    def test_author_can_always_view(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(days=1))
        self.client.login(username="jun", password="pass1234")
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertTrue(response.context["can_view"])

    def test_after_answer_type_visible_once_answered_in_session(self):
        problem = self._make_problem(Problem.AFTER_ANSWER, timedelta(days=1))
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertFalse(response.context["can_view"])

        self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {
                "nickname": "こだぬき",
                "rank": self.rank.pk,
                "move": "qf",
                "body": "",
            },
        )
        response = self.client.get(reverse("answer_list", kwargs={"pk": problem.pk}))
        self.assertTrue(response.context["can_view"])
        self.assertEqual(AnswerPost.objects.count(), 1)

    def test_closed_after_deadline_blocks_new_answers(self):
        problem = self._make_problem(Problem.AFTER_DEADLINE, timedelta(seconds=-1))
        response = self.client.post(
            reverse("answer_create", kwargs={"pk": problem.pk}),
            {"nickname": "x", "rank": self.rank.pk, "move": "qf", "body": ""},
        )
        self.assertEqual(AnswerPost.objects.count(), 0)
        self.assertContains(response, "締切を過ぎました")


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

        self.client.post(reverse("problem_delete", kwargs={"pk": problem.pk}), {"next": "archive_problems"})
        self.assertFalse(Problem.objects.filter(pk=problem.pk).exists())

    def test_cannot_operate_on_others_problem(self):
        other = User.objects.create_user(username="liz", email="l@example.com", password="pass1234", is_active=True)
        problem = Problem.objects.create(
            author=other, title="他人の問題", board_sgf="AB[pd]", turn=Problem.BLACK,
            deadline=timezone.now() + timedelta(days=1), disclosure_type=Problem.AFTER_DEADLINE,
        )
        response = self.client.post(reverse("problem_close", kwargs={"pk": problem.pk}))
        self.assertEqual(response.status_code, 404)


class RankSeedTests(TestCase):
    def test_kyu_then_dan_order(self):
        labels = list(Rank.objects.order_by("sort_order").values_list("label", flat=True))
        self.assertEqual(labels[0], "1級")
        self.assertEqual(labels[14], "15級")
        self.assertEqual(labels[15], "初段")
        self.assertEqual(labels[-1], "8段")
