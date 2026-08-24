"""
Regression tests for DatabaseManager.get_daily_checkins_current_month(),
which feeds the Dashboard's "Daily Check-ins This Month" chart.

Covers:
- Multiple visitors on the same day are summed correctly.
- Days with zero check-ins are still present (0), not omitted.
- The range always spans the 1st of the current month through today.
- Visitors from a previous/next month never leak into the result.
- date.today() (LOCAL date), not SQLite's UTC 'now', is the source of
  truth for "this month"/"today", matching the rest of the app.
"""
import os
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database as database_module
from database import DatabaseManager

_REAL_DATE = date


class _FixedDate(_REAL_DATE):
    """A date subclass whose today() always returns a fixed calendar date,
    so tests don't depend on when they happen to run."""
    _fixed_today = _REAL_DATE(2026, 8, 24)

    @classmethod
    def today(cls):
        return cls._fixed_today


class TestDailyCheckinsCurrentMonth(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = os.path.join(self._tmp_dir.name, "test_visitors.db")
        self.db = DatabaseManager(db_path=db_path)

    def tearDown(self):
        self._tmp_dir.cleanup()

    def _add_visitor_on(self, dt: datetime, nric_suffix: str):
        ok = self.db.add_visitor(
            nric=f"S{nric_suffix}D",
            hp_no="81234567",
            first_name="Test",
            last_name="Visitor",
            category="Visitor",
            purpose="Meeting",
            destination="Level 1",
            company="Acme",
            vehicle_number="",
            pass_number=self.db.generate_pass_number(),
            id_number=None,
            remarks="",
            person_visited="Someone",
            organization="",
            check_in_time=dt,
        )
        self.assertTrue(ok, f"Failed to insert test visitor at {dt}")

    def _fixed_today(self, day: int, month: int = 8, year: int = 2026):
        _FixedDate._fixed_today = _REAL_DATE(year, month, day)
        return patch.object(database_module, "date", _FixedDate)

    def test_full_range_includes_zero_checkin_days(self):
        with self._fixed_today(24):
            # Visitors on Aug 20 (x2), Aug 21 (x4), Aug 23 (x1), Aug 24 (x3).
            # Aug 22 and every other day in range intentionally has none.
            self._add_visitor_on(datetime(2026, 8, 20, 10, 0), "0000001")
            self._add_visitor_on(datetime(2026, 8, 20, 11, 0), "0000002")
            for i in range(4):
                self._add_visitor_on(datetime(2026, 8, 21, 9, i), f"000001{i}")
            self._add_visitor_on(datetime(2026, 8, 23, 13, 0), "0000030")
            for i in range(3):
                self._add_visitor_on(datetime(2026, 8, 24, 14, i), f"000004{i}")

            result = self.db.get_daily_checkins_current_month()

        # One entry per day, Aug 1 -> Aug 24 inclusive.
        self.assertEqual(len(result), 24)
        self.assertEqual(result[0][0], date(2026, 8, 1))
        self.assertEqual(result[-1][0], date(2026, 8, 24))

        counts = dict(result)
        self.assertEqual(counts[date(2026, 8, 20)], 2)
        self.assertEqual(counts[date(2026, 8, 21)], 4)
        self.assertEqual(counts[date(2026, 8, 22)], 0)  # zero-checkin day preserved
        self.assertEqual(counts[date(2026, 8, 23)], 1)
        self.assertEqual(counts[date(2026, 8, 24)], 3)
        # Every untouched day earlier in the month is present with count 0.
        self.assertEqual(counts[date(2026, 8, 1)], 0)
        self.assertEqual(counts[date(2026, 8, 19)], 0)

        # Every value must be a real datetime.date, not a string/number.
        for d, _ in result:
            self.assertIsInstance(d, date)

    def test_previous_month_visitor_does_not_leak_in(self):
        with self._fixed_today(24):
            self._add_visitor_on(datetime(2026, 7, 31, 23, 59), "0000099")  # previous month
            self._add_visitor_on(datetime(2026, 8, 1, 0, 1), "0000098")     # this month, day 1

            result = self.db.get_daily_checkins_current_month()

        counts = dict(result)
        self.assertNotIn(date(2026, 7, 31), counts)
        self.assertEqual(counts[date(2026, 8, 1)], 1)
        self.assertEqual(sum(c for _, c in result), 1)

    def test_first_day_of_month_is_today_yields_single_day_range(self):
        with self._fixed_today(1):
            self._add_visitor_on(datetime(2026, 8, 1, 9, 0), "0000050")
            result = self.db.get_daily_checkins_current_month()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], (date(2026, 8, 1), 1))

    def test_no_visitors_still_returns_full_zero_filled_range(self):
        with self._fixed_today(24):
            result = self.db.get_daily_checkins_current_month()

        self.assertEqual(len(result), 24)
        self.assertTrue(all(c == 0 for _, c in result))

    def test_result_uses_local_today_not_sqlite_utc_now(self):
        # Regression guard: the query must not rely on SQLite's 'now'
        # (UTC) for determining "this month"; it must use the same local
        # date.today() as the rest of the app (e.g. get_todays_checkin_count).
        with self._fixed_today(24):
            self._add_visitor_on(datetime(2026, 8, 24, 12, 0), "0000060")
            result = self.db.get_daily_checkins_current_month()
            month_start = date(2026, 8, 1)
            today = date(2026, 8, 24)

        self.assertEqual(result[0][0], month_start)
        self.assertEqual(result[-1][0], today)


if __name__ == "__main__":
    unittest.main()
