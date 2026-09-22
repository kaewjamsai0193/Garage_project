from decimal import ROUND_HALF_UP, Decimal


def round_money(x) -> Decimal:
    """ปัดเงินเป็นทศนิยม 2 ตำแหน่งแบบปัดครึ่งขึ้น"""
    return Decimal(x).quantize(Decimal("0.01"), ROUND_HALF_UP)


def format_qty(d) -> str:
    """แปลงจำนวนเป็นข้อความไม่มีศูนย์ท้าย (เช่น 2.500 → "2.5") ใช้ในข้อความ error"""
    return f"{Decimal(d).normalize():f}"
