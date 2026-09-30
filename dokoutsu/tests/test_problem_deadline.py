"""4a 問題投稿画面: 締切の初期値のテスト(docs/test/4a_問題投稿画面.md 7章)"""

from unittest import mock

from django.test import TestCase


class DeadlineInitialTests(TestCase):
    def _initial_at(self, local_dt):
        from zoneinfo import ZoneInfo

        from ..forms import ProblemForm

        aware = local_dt.replace(tzinfo=ZoneInfo("Asia/Tokyo"))
        with mock.patch("django.utils.timezone.now", return_value=aware):
            form = ProblemForm()
        return form.initial["deadline_date"], form.initial["deadline_hour"], form.initial["deadline_minute"]

    def test_rounds_up_to_next_10_minutes(self):
        import datetime

        self.assertEqual(
            self._initial_at(datetime.datetime(2026, 9, 29, 14, 3, 30)),
            (datetime.date(2026, 9, 29), 14, 10),
        )

    def test_exact_10_minutes_goes_to_next_slot(self):
        import datetime

        self.assertEqual(
            self._initial_at(datetime.datetime(2026, 9, 29, 14, 10, 0)),
            (datetime.date(2026, 9, 29), 14, 20),
        )

    def test_crosses_midnight(self):
        import datetime

        self.assertEqual(
            self._initial_at(datetime.datetime(2026, 9, 29, 23, 55, 0)),
            (datetime.date(2026, 9, 30), 0, 0),
        )
