from decimal import Decimal

from app.money import (invoice_totals, labor_net_ex_vat, purchase_vat,
                       split_vat, suggested_withholding, unit_cost)


def test_split_vat_adds_back_to_total():
    for total in ("1070", "3800", "600", "4280.55"):
        base, vat = split_vat(total, 7)
        assert base + vat == Decimal(total)      # กฎข้อเดียวที่ห้ามพังทุกกรณี


def test_split_vat_known_numbers():
    assert split_vat("1070", 7) == (Decimal("1000.00"), Decimal("70.00"))
    assert split_vat("3800", 7) == (Decimal("3551.40"), Decimal("248.60"))


def test_purchase_vat():
    assert purchase_vat("856", 7) == Decimal("56.00")


def test_unit_cost_keeps_four_places():
    assert unit_cost("1000", 3) == Decimal("333.3333")


def test_withholding_is_on_labor_only():
    # อะไหล่ 3,210 + ค่าแรง 1,070 ไม่มีส่วนลด → ค่าแรงก่อน VAT 1,000 → หัก 30
    labor_net = labor_net_ex_vat("1070", 0, "4280", 7)
    assert labor_net == Decimal("1000.00")
    assert suggested_withholding(labor_net) == Decimal("30.00")


def test_withholding_after_bill_discount():
    # ยอดเดิม ลดทั้งบิล 428 → ส่วนแบ่งของค่าแรง 107 → สุทธิก่อน VAT 900 → หัก 27
    labor_net = labor_net_ex_vat("1070", "428", "4280", 7)
    assert labor_net == Decimal("900.00")
    assert suggested_withholding(labor_net) == Decimal("27.00")


def test_zero_lines_does_not_divide_by_zero():
    assert labor_net_ex_vat(0, 0, 0, 7) == Decimal("0.00")