from decimal import ROUND_HALF_UP, Decimal

def q2(x) -> Decimal:
    """คำนวณทศนิยม 2 ตำแหน่ง"""
    return Decimal(x).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def q4(x) -> Decimal:
    """คำนวณทศนิยม 4 ตำแหน่ง"""
    return Decimal(x).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

def line_total(qty, unit_price) -> Decimal:
    """คำนวณราคาสุทธิของบรรทัดสินค้า"""
    return q2(qty * unit_price)

def split_vat(grand_total, rate) -> tuple[Decimal, Decimal]:
    """แยก VAT ออกจากราคาสุทธิ"""
    grand_total = Decimal(grand_total)
    subtotal = q2(grand_total / (1 + Decimal(rate) / 100))
    return subtotal, grand_total - subtotal

def purchase_vat(total_paid, rate) -> Decimal:
    """คำนวณ VAT ของราคาสุทธิ"""
    total_paid = Decimal(total_paid)
    return total_paid - q2(total_paid * 100 / (100 + Decimal(rate)))

def unit_cost(cost_total, qty) -> Decimal:
    """คำนวณราคาต้นทุนต่อหน่วย"""
    return q4(Decimal(cost_total) / Decimal(qty))

def qty_str(d) -> str:
    """แปลงจำนวนเป็น string โดยไม่เอาศูนย์ต่อท้าย"""
    return f"{Decimal(d).normalize():f}"

def invoice_totals(line_totals, discount, rate) -> tuple[Decimal, Decimal, Decimal]:
    """คำนวณยอดรวมของบิล"""
    grand = sum((Decimal(x) for x in line_totals), Decimal(0)) - Decimal(discount)
    subtotal, vat = split_vat(grand, rate)
    return grand, subtotal, vat

def labor_net_ex_vat(labor, discount, lines_sum, rate) -> Decimal:
    """ค่าแรงหลังหักส่วนแบ่งส่วนลดทั้งบิล ก่อน VAT"""
    if Decimal(lines_sum) == 0:
        return Decimal("0.00")
    share = q2(Decimal(discount) * Decimal(labor) / Decimal(lines_sum))
    return q2((Decimal(labor) - share) / (1 + Decimal(rate) / 100))

def suggested_withholding(labor_net) -> Decimal:
    """คำนวณภาษีหัก ณ ที่จ่าย 3% ของค่าแรงหลัง VAT"""
    return q2(Decimal(labor_net) * 3 / 100)