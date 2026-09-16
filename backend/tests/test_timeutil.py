from datetime import date, datetime, timezone

from app.timeutil import add_months, bkk_date


def test_late_night_utc_is_next_day_in_thailand():
    # 31 ธ.ค. 17:30 UTC = 1 ม.ค. 00:30 เวลาไทย → ต้องเป็นวันปีใหม่
    assert bkk_date(datetime(2026, 12, 31, 17, 30, tzinfo=timezone.utc)) == date(2027, 1, 1)


def test_add_months_clamps_to_end_of_month():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 8, 15), 6) == date(2027, 2, 15)