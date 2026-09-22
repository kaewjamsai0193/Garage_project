# เฟส 5–10 (ฉบับเก่า ยังไม่ปรับ)

ไฟล์ในโฟลเดอร์นี้เขียนตาม**โครงเก่า** (`routers/` `services/` `schemas/`) และคิดว่าเฟส 1–4 ทำของเผื่อไว้ให้แล้ว
ชุดใหม่เฟส 0–4 **ตัดของเผื่อทิ้งหมด** เวลาจะทำเฟส 5 ขึ้นไป ต้องเติมของข้างล่างนี้ก่อน

## เปลี่ยน path ตามโครงใหม่

| ในไฟล์เก่า | ในโครงใหม่ |
|---|---|
| `app/routers/xxx.py` | `app/xxx/router.py` |
| `app/services/xxx.py` | `app/xxx/service.py` |
| `app/schemas/xxx.py` | `app/xxx/schemas.py` |
| `app/schemas/__init__.py` | `app/schemas.py` |
| `from app.services.stock import issue_fifo` | `from app.stock.service import issue_fifo` |
| `digits()` ใน `services/purchasing.py` | `app/textutil.py` |

## ของที่ชุดใหม่ยังไม่ได้ทำ (เติมตอนเฟสที่ใช้จริง)

| ของ | ใช้ครั้งแรกเฟส | ต้องทำอะไร |
|---|---|---|
| `GET /api/users/mechanics` | 5 | เพิ่มใน `users/router.py` |
| `_locked_lots` · `issue_fifo` · `return_issued` | 5 | เพิ่มใน `stock/service.py` (โค้ดอยู่ใน `../../project/backend/app/stock/service.py`) |
| `stock_movements.job_id` · `invoice_item_id` · ประเภท `issue` `return` | 5–6 | เพิ่มคอลัมน์ + **แก้ CHECK `type` `direction` เพิ่ม CHECK `reference` ด้วยมือใน migration** (วิธีเดียวกับเฟส 4) · `MovementOut` + หน้า StockDetail เพิ่ม `job_id` `invoice_item_id` |
| fixture `stock` ใน `conftest.py` | 5 | ใส่ของเข้าคลังผ่าน `adjust_up` |
| `textutil.no_spaces()` | 5 | ทะเบียนรถ |
| `timeutil.py` (+ `test_timeutil.py`) | 6 | เวลาไทย ปีเลขบิล |
| `money.split_vat` `invoice_totals` `labor_net_ex_vat` `suggested_withholding` | 6 | + เทสต์ |
| `settings.repair_warranty_days` | 6–7 | คอลัมน์ + schema + ช่องในหน้าตั้งค่า |
| `products.maintenance_cycle_months` | 8 | คอลัมน์ + CHECK + schema + ช่องในฟอร์มสินค้า |
| `settings.dead_stock_days` | 9 | คอลัมน์ + schema + ช่องในหน้าตั้งค่า |
| `components/PrintLayout.jsx` | 5 (ใบเสนอราคา) | ดึงหัวกระดาษ A4 ออกจาก `PrintPOPage.jsx` เป็นคอมโพเนนต์ (ตอนนั้นใช้ 2 ที่แล้ว) |
| `ProductSearch` prop `showPrice` `autoFocus` | 5 | แสดงราคาขายตอนเลือกอะไหล่เข้าใบงาน/ขาย |
| `ReasonDialog` prop `reasonLabel` `required` `initialReason` `confirmLabel` | 6 | กล่องยืนยันแบบไม่ต้องกรอกเหตุผล |
| `api.js` `thaiDateTime` `VEHICLE_TYPE` `carName` · `components/Info.jsx` | 5 | |
| เมนู `AppLayout.jsx` | 5+ | ชุดใหม่ใช้แถบข้าง + ลิ้นชัก ☰ บนมือถือ (ไม่มีแถบล่าง ไม่มีหน้า More) เติมเมนูใน `MENU` ทีละบรรทัด ถ้าเมนูเยอะจนยาวค่อยแบ่งหัวข้อกลุ่ม · หน้าแรก `/` เปลี่ยนไป `/jobs` · ไฟล์เก่าที่พูดถึงแถบล่าง, `mobile`, `MorePage.jsx` ให้ข้าม |
