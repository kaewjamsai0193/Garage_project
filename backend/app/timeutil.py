import calendar
from datetime import date, datetime, timedelta, timezone

BKK = timezone(timedelta(hours=7), "Asia/Bangkok")

def now() -> datetime:
    return datetime.now(timezone.utc)

def bkk_date(dt: datetime) -> date:
    return dt.astimezone(BKK).date()

def today() -> date:
    return bkk_date(now())

def add_months(d: date, months:int) -> date:
    index = d.month - 1 + months
    year, month = d.year + index // 12, index % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))

