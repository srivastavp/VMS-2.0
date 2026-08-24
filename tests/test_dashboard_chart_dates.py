"""
Regression tests for the "Daily Check-ins This Month" dashboard chart's
date handling.

These specifically guard against the bug where the X-axis displayed raw
numeric values like "26.811116" instead of calendar dates: parse_chart_date()
used isinstance(d, datetime), which is False for a plain datetime.date
(what DatabaseManager.get_daily_checkins_current_month() actually
returns), so every point silently fell back to `datetime.today()`
called once per point -- collapsing the whole axis onto near-identical
microsecond-apart timestamps. With an almost-zero-width date range,
Matplotlib's date locator/formatter can't produce day ticks and falls
back to raw numeric offsets.
"""
import os
import sys
import unittest
from datetime import date, datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.qt_app import get_app  # noqa: F401 (ensures a QApplication exists)

from ui.dashboard import parse_chart_date, DashboardWidget


class TestParseChartDate(unittest.TestCase):
    def test_datetime_passthrough(self):
        dt = datetime(2026, 8, 24, 10, 30)
        self.assertEqual(parse_chart_date(dt), dt)

    def test_date_is_converted_to_datetime_at_midnight(self):
        # This is the exact case that used to break: datetime.date is NOT
        # an instance of datetime.datetime.
        d = date(2026, 8, 24)
        result = parse_chart_date(d)
        self.assertIsInstance(result, datetime)
        self.assertEqual(result, datetime(2026, 8, 24, 0, 0, 0))

    def test_iso_string_is_parsed(self):
        result = parse_chart_date("2026-08-24")
        self.assertEqual(result, datetime(2026, 8, 24))

    def test_alternate_string_formats_are_parsed(self):
        self.assertEqual(parse_chart_date("24-08-2026"), datetime(2026, 8, 24))
        self.assertEqual(parse_chart_date("2026/08/24"), datetime(2026, 8, 24))

    def test_unparseable_value_returns_none_not_today(self):
        # Must NOT silently substitute today's date -- that's what
        # corrupted the whole chart's axis range in the original bug.
        self.assertIsNone(parse_chart_date(12345))
        self.assertIsNone(parse_chart_date(None))
        self.assertIsNone(parse_chart_date("not-a-date"))

    def test_sequence_of_dates_stays_spread_out(self):
        # Regression guard for the exact reported symptom: a real list of
        # distinct calendar dates must parse to distinct datetimes spread
        # across the correct range, not collapse to ~identical "now" values.
        days = [date(2026, 8, d) for d in range(20, 25)]
        parsed = [parse_chart_date(d) for d in days]
        self.assertEqual(parsed, [datetime(2026, 8, d) for d in range(20, 25)])
        span_seconds = (parsed[-1] - parsed[0]).total_seconds()
        self.assertGreater(span_seconds, 3600)  # spans real days, not microseconds


class TestDashboardChartRendersRealDates(unittest.TestCase):
    """
    End-to-end check that DashboardWidget.update_chart() renders actual
    calendar-date tick labels, not raw numeric offsets, given data shaped
    exactly like DatabaseManager.get_daily_checkins_current_month()'s
    real return value (a list of (datetime.date, int) tuples).
    """

    class _FakeDb:
        def get_todays_checkin_count(self):
            return 0

        def get_active_visitors(self):
            return []

        def get_average_duration(self):
            return 0

        def get_daily_checkins_current_month(self):
            return [
                (date(2026, 8, 20), 2),
                (date(2026, 8, 21), 4),
                (date(2026, 8, 22), 0),
                (date(2026, 8, 23), 1),
                (date(2026, 8, 24), 3),
            ]

    def test_chart_x_axis_shows_calendar_dates_not_raw_numbers(self):
        widget = DashboardWidget(self._FakeDb())
        try:
            ax = widget.figure.axes[0]
            widget.figure.canvas.draw()
            labels = [t.get_text() for t in ax.get_xticklabels() if t.get_text()]

            self.assertTrue(labels, "Expected at least one X-axis tick label")
            for label in labels:
                # The original bug produced labels like "26.811116" --
                # plain decimal numbers. Real calendar-date labels always
                # contain a non-digit, non-dot character (e.g. "Aug 20").
                self.assertFalse(
                    label.replace(".", "").replace("-", "").isdigit(),
                    f"X-axis label looks like a raw number, not a date: {label!r}",
                )

            # The plotted line's X data must be real dates spanning the
            # expected range, not collapsed to near-identical values.
            line = ax.lines[0]
            xdata = list(line.get_xdata())
            span = max(xdata) - min(xdata)
            span_days = span.total_seconds() / 86400 if hasattr(span, "total_seconds") else span
            self.assertGreater(span_days, 1)  # spans multiple days
        finally:
            widget.deleteLater()


if __name__ == "__main__":
    unittest.main()
