from decimal import Decimal

from app.money import format_qty, round_money


def test_round_money_rounds_half_up():
    assert round_money("2.345") == Decimal("2.35")  # float ปัดแบบธนาคารได้ 2.34
    assert round_money(Decimal("1.5") * Decimal("33.333")) == Decimal("50.00")


def test_format_qty_drops_trailing_zeros():
    assert format_qty(Decimal("2.000")) == "2"
    assert format_qty(Decimal("0.500")) == "0.5"
    assert format_qty(Decimal("100")) == "100"  # ไม่กลายเป็น 1E+2
