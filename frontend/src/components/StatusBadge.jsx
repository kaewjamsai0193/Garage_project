const STATUS = {
  active: ["ใช้งาน", "ok"],
  disabled: ["ปิดใช้งาน", "neutral"],
  low: ["ถึงจุดเตือน", "warn"],
  inactive: ["เลิกใช้", "neutral"],
};

// สถานะสินค้า: เลิกใช้ → inactive, คงเหลือ ≤ ขั้นต่ำ → low, ปกติ → null
export function productStatus(p) {
  if (!p.is_active) return "inactive";
  const hasMinimum = Number(p.min_stock) > 0;
  if (hasMinimum && Number(p.qty_on_hand) <= Number(p.min_stock)) return "low";
  return null;
}

// ป้ายสถานะตาม key ใน STATUS (null = ไม่แสดง)
export default function StatusBadge({ status }) {
  if (!status) return null;
  const [text, tone] = STATUS[status];
  return <span className={`badge badge-${tone}`}>{text}</span>;
}
