# เฟส 2 — ผู้ใช้ และค่าตั้ง

**จบเฟสนี้แล้วจะทำอะไรได้**

- admin สร้าง / แก้ / ปิดบัญชีช่างกับพนักงานได้
- ตั้งชื่ออู่ ที่อยู่ เลขประจำตัวผู้เสียภาษี อัตรา VAT ได้เองจากหน้าจอ
- ล็อกอินเป็นช่างแล้วเข้าหน้าตั้งค่าไม่ได้**จริง ๆ** — กันทั้งหน้าจอและ API

## เฟสนี้ข้อมูลเดินยังไง (อ่าน 1 นาที)

```
admin กรอกฟอร์มผู้ใช้ / ค่าตั้งอู่
   ↓ หน้าจอส่งไป POST /api/users · PATCH /api/users/{id} · PUT /api/settings
backend เช็คก่อนว่าคนที่ส่งมาเป็น admin จริงไหม (ไม่ใช่ → 403 ไม่ทำให้)
   ↓ ผ่าน → เช็คกฎธุรกิจ (ชื่อซ้ำไหม · ปิดบัญชีตัวเองอยู่หรือเปล่า)
เขียนลงตาราง users / settings
   ↓ ตอบข้อมูลที่บันทึกแล้วกลับมา
หน้าจอบอก cache ว่า "ข้อมูลผู้ใช้เก่าแล้ว" → รายการข้างหลังโหลดใหม่เอง
```

- **เพิ่มอะไรในฐาน** ตาราง `settings` ที่มีแถวเดียวตลอดชีวิตระบบ (ชื่ออู่ · ที่อยู่ · เลขผู้เสียภาษี · อัตรา VAT)
- **ทำไมค่าตั้งต้องอยู่ในฐาน** เจ้าของอู่แก้เองได้จากหน้าจอ ไม่ต้องแก้โค้ดแล้ว deploy ใหม่
- **ไม่มีการลบผู้ใช้** มีแต่ปิดใช้งาน เพราะเอกสารเก่าอ้างถึงชื่อคนนั้นอยู่
- **หน้าจอซ่อนเมนูตามบทบาท** เป็นแค่ความสะดวก ของจริงที่กันคือ backend

**อ่านก่อนเริ่ม** `data_model.md` หัวข้อ 1 และหัวข้อ "สิทธิ์ตรวจที่เซิร์ฟเวอร์"

**เฟสนี้ใช้เวลานาน เพราะเป็นเฟสที่สร้างของกลาง** — ข้อ 8-15 คือคอมโพเนนต์
(ป๊อปอัพ · หน้ารายการ · ป้ายสถานะ · ช่องกรอก) ที่**ทุกเฟสหลังจากนี้ใช้ซ้ำ**
ลงแรงตรงนี้ทีเดียว เฟส 3-9 จะเร็วขึ้นมาก

**เฟสนี้ยังไม่ทำ** (ตั้งใจข้าม ไม่ใช่ลืม)

- วันรับประกันงานซ่อม กับ เกณฑ์ของค้างคลัง — ค่าตั้งสองตัวนี้ใช้ครั้งแรกเฟส 6 กับ 9
  ค่อยเพิ่มคอลัมน์ตอนนั้น เพิ่มตอนนี้ก็เป็นช่องว่าง ๆ ที่ไม่มีใครใช้
- รายชื่อช่างสำหรับเลือกในใบงาน (`/users/mechanics`) — เฟส 5

---

# ส่วน backend

## 1. `app/db.py` — เติม `get_or_404`

**ขั้นนี้ทำอะไร** ต่อจากนี้จะมี endpoint ที่รับ id มาจาก URL เยอะมาก (`/api/users/5`)
ทุกอันต้องเช็คก่อนว่า id นั้นมีอยู่จริงไหม ไม่งั้นโค้ดบรรทัดถัดไปจะพังเพราะได้ `None`
เขียนตัวช่วยไว้ตัวเดียว แล้วเรียกใช้ทุกที่

**เปิด** `app/db.py` → แก้บรรทัด import ข้างบนให้เป็นแบบนี้

```python
from fastapi import HTTPException
from sqlalchemy import MetaData, create_engine
```

→ แล้วเลื่อนไปท้ายไฟล์ วางฟังก์ชันนี้ต่อท้าย

```python
def get_or_404(db, model, id, label):
    """ดึงแถวจาก DB ตาม id ถ้าไม่เจอโยน 404 ไม่พบ{label}"""
    obj = db.get(model, id)
    if obj is None:
        raise HTTPException(404, f"ไม่พบ{label}")
    return obj
```

**อ่านโค้ดนี้ยังไง**

`db.get(model, id)` หาแถวจาก primary key ถ้าไม่เจอมันคืน `None` เฉย ๆ ไม่ฟ้องอะไร
เราเลยเช็ค `None` เอง แล้วโยน `HTTPException(404, ...)` ให้ FastAPI แปลงเป็น
HTTP 404 พร้อมข้อความไทยส่งกลับหน้าจอ

`label` คือคำที่เอาไปต่อท้าย `"ไม่พบ"` — เรียกใช้จริงจะเป็นแบบนี้:

```python
user = get_or_404(db, User, user_id, "ผู้ใช้")      # ไม่เจอ → 404 "ไม่พบผู้ใช้"
item = get_or_404(db, Item, item_id, "สินค้า")      # ไม่เจอ → 404 "ไม่พบสินค้า"
```

เขียนที่เดียวแบบนี้ ข้อความที่ผู้ใช้เห็นเลยเป็นรูปแบบเดียวกันทั้งระบบ
ไม่ใช่หน้าหนึ่ง "ไม่พบผู้ใช้" อีกหน้า "user not found"

## 2. `app/models.py` — เพิ่มตาราง `settings`

**ขั้นนี้ทำอะไร** ชื่ออู่ ที่อยู่ เลขผู้เสียภาษี อัตรา VAT — ของพวกนี้เจ้าของต้องแก้เองได้
โดยไม่ต้องเรียกโปรแกรมเมอร์ เลยต้องเก็บในฐานข้อมูล ไม่ใช่ฝังไว้ในโค้ด
ขั้นนี้สร้างตารางที่เก็บมัน

**เปิด** `app/models.py` → แก้บรรทัด import ข้างบน แล้วเพิ่มบรรทัด `RATE` ไว้ใต้ import

```python
from decimal import Decimal

from sqlalchemy import CheckConstraint, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

RATE = Numeric(5, 2)
```

→ แล้วเลื่อนไปท้ายไฟล์ วางคลาสนี้ต่อท้าย

```python
class Setting(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    shop_name: Mapped[str] = mapped_column(String(200), server_default="")
    shop_address: Mapped[str] = mapped_column(Text, server_default="")
    shop_tax_id: Mapped[str] = mapped_column(String(20), server_default="")
    vat_rate: Mapped[Decimal] = mapped_column(RATE, server_default="7")
    __table_args__ = (
        CheckConstraint("id = 1", name="single_row"),
        CheckConstraint("vat_rate >= 0", name="vat_rate"),
    )
```

**อ่านโค้ดนี้ยังไง**

ตารางนี้แปลกกว่าตารางอื่นตรงที่ **มันมีได้แถวเดียวเท่านั้น** ตลอดชีวิตของระบบ
เพราะอู่มีอู่เดียว ค่าตั้งก็มีชุดเดียว บังคับด้วยสองบรรทัดนี้:

```python
id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
#                                                 ^ ฐานจะไม่แจกเลขให้เอง ต้องระบุเอง
CheckConstraint("id = 1", name="single_row")
#               ^ และเลขที่ระบุได้มีแค่ 1 → แถวที่สองใส่ไม่ได้เลย
```

ผลคือทั้งระบบอ่านค่าตั้งด้วย `db.get(Setting, 1)` ได้เสมอ ไม่ต้องเผื่อกรณี
"มีหลายแถวเอาอันไหนดี" หรือ "ยังไม่มีสักแถว"

**`RATE = Numeric(5, 2)` — ห้ามใช้ `Float` กับเงินและอัตราเด็ดขาด**

`Float` เก็บเลขทศนิยมแบบประมาณค่า ลองเปิด python พิมพ์ดูได้:

```
>>> 0.1 + 0.2
0.30000000000000004      ← ไม่ใช่ 0.3
```

ทีละแถวไม่เห็นอะไร แต่พอบวกใบเสร็จเป็นพันใบ สตางค์จะเพี้ยนจนยอดไม่ตรง
`Numeric` เก็บเป็นตัวเลขจริง ไม่ปัด — `(5, 2)` แปลว่า 5 หลักรวม ทศนิยม 2 ตำแหน่ง
พอสำหรับ `7.00` หรือ `100.00`

> **ทำไม VAT ต้องอยู่ในฐานข้อมูล แทนที่จะเขียน `VAT = 7` ในโค้ด**
> อัตรา VAT เปลี่ยนได้ตามกฎหมาย วันนั้นถ้าฝังในโค้ดต้องแก้โค้ดแล้ว deploy ใหม่
> อยู่ในค่าตั้ง เจ้าของแก้เองได้จากหน้าจอ · เฟส 4 จะเอาไปใช้ตอนถอด VAT จากราคาซื้อ

> **ทำไมไม่มีช่อง `updated_at` / `updated_by` ว่าใครแก้ล่าสุด**
> อู่นี้มี admin คนเดียวที่แก้ค่าตั้งได้ (เดี๋ยวข้อ 5 จะล็อก PUT ไว้เฉพาะ admin)
> "ใครแก้" เลยตอบได้คำตอบเดียวตลอด ไม่ต้องเก็บ
> ส่วน "แก้เมื่อไหร่" ช่องเดียวมันโดนทับทุกครั้งที่กดบันทึก ตอบได้แค่ครั้งล่าสุด
> ซึ่งไม่ช่วยตอบคำถามที่คนอยากรู้จริง ๆ คือ "บิลใบเก่าคิด VAT กี่เปอร์เซ็นต์"
> คำถามนั้นเฟส 4 แก้ด้วยการเก็บ `vat_amount` ลงในตัวเอกสารไปเลย
> วันที่มี admin หลายคนจริง ๆ ค่อยทำตาราง `audit_log` ตารางเดียวคลุมทุกตาราง
> ดีกว่าไปแปะ `updated_by` / `updated_at` ทีละตาราง

### migration — บอกฐานข้อมูลจริงให้สร้างตารางตาม

เขียนคลาสใน `models.py` เฉย ๆ ฐานข้อมูลยังไม่รู้เรื่องด้วย ต้องสั่ง alembic
ให้ไปเทียบว่าโค้ดกับฐานต่างกันตรงไหน แล้วเขียนไฟล์คำสั่งแก้ฐานออกมาให้

```
docker compose run --rm api alembic revision --autogenerate -m "settings"
```

ได้ไฟล์ใหม่มาหนึ่งไฟล์ใน `backend/alembic/versions/` (ชื่อขึ้นต้นด้วยรหัสสุ่ม)

**ห้ามเพิ่งสั่ง upgrade — ต้องแก้ไฟล์นั้นก่อน** เปิดขึ้นมา หาบรรทัด
`# ### end Alembic commands ###` ใน `upgrade()` แล้วเติมบรรทัด insert ไว้ข้างบนมัน

```python
def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('settings',
    ...
    )
    op.execute("insert into settings (id) values (1)")   # ← เพิ่มบรรทัดนี้
    # ### end Alembic commands ###
```

**ทำไมต้องเติมบรรทัดนี้เอง** — alembic สร้างได้แค่ "ตารางเปล่า" แต่ตารางนี้
ต้องมีแถว id 1 อยู่ก่อนเสมอ เพราะโค้ดทุกที่จะอ่านด้วย `db.get(Setting, 1)`
ถ้าไม่มีแถวนั้น หน้าตั้งค่าจะพังทันทีที่เปิดครั้งแรก

ใส่ไว้ใน migration แบบนี้ ทุกฐานข้อมูล (เครื่องเราเอง เครื่องที่รันเทสต์ เครื่องจริง)
ได้แถวนี้เองอัตโนมัติตอน upgrade ไม่ต้องจำว่าต้องไปเพิ่มมือ

ไม่ต้องใส่ค่าอื่นเลย เพราะทุกคอลัมน์มี `server_default` อยู่แล้ว (ชื่ออู่เป็น `""` VAT เป็น `7`)
และ `downgrade()` ก็ไม่ต้องแก้ เพราะ `drop_table` มันลบทั้งตารางรวมแถวอยู่แล้ว

สั่ง upgrade แล้วเช็คว่าได้แถวจริง:

```
docker compose run --rm api alembic upgrade head
docker compose exec db psql -U garage -d garage -c "select * from settings"   # 1 แถว vat_rate 7.00
```

## 3. `app/auth.py` — ใส่ตัวตรวจสิทธิ์ `require_role`

**ขั้นนี้ทำอะไร** เฟส 1 ระบบตรวจได้แค่ "ล็อกอินหรือยัง" แต่ยังตรวจไม่ได้ว่า
"คนที่ล็อกอินมาเป็น admin ไหม" ขั้นนี้เพิ่มตัวตรวจบทบาท

**เปิด** `app/auth.py` → เลื่อนไปท้ายสุด → วางต่อท้าย

```python
def require_role(*roles):
    """สร้าง Dependency ที่เช็ค role ของ current_user, ไม่อยู่ใน roles โยน 403"""

    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "ไม่มีสิทธิ์ทำรายการนี้")
        return user
    return dep
```

**อ่านโค้ดนี้ยังไง**

สังเกตว่า `require_role` ไม่ได้ตรวจสิทธิ์เอง — มันไป **สร้างตัวตรวจ** ขึ้นมาคืนให้
(ฟังก์ชัน `dep` ข้างใน) เรียกครั้งเดียว เก็บไว้ใช้ซ้ำได้:

```python
admin = require_role("admin")                # ผ่านเฉพาะ admin
staff = require_role("admin", "employee")    # ผ่านทั้งสองบทบาท (เฟส 3 ใช้)
```

แล้วเอาไปแปะที่ endpoint ที่อยากล็อก:

```python
def list_users(user = Depends(admin)):       # ไม่ใช่ admin → ไม่ได้เข้าถึงบรรทัดนี้เลย
```

ลำดับที่ FastAPI ตรวจให้:

1. มันเห็น `Depends(current_user)` อยู่ข้างใน `dep` → ตรวจ token ก่อน
   ไม่มี token หรือหมดอายุ → **401 ยังไม่ได้ล็อกอิน**
2. ผ่านข้อ 1 แล้วค่อยเช็ค `user.role` → บทบาทไม่ตรง → **403 ไม่มีสิทธิ์**

สองรหัสนี้คนละความหมาย: 401 = "คุณเป็นใครไม่รู้" · 403 = "รู้ว่าคุณเป็นใคร แต่คุณทำอันนี้ไม่ได้"

> **ทำไมต้องตรวจที่เซิร์ฟเวอร์ ทั้งที่เดี๋ยวหน้าจอก็ซ่อนเมนูให้แล้ว**
> การซ่อนปุ่มกันได้แค่คนที่ไม่ได้ตั้งใจจะเข้า
> ใครก็ตามที่เปิด DevTools ยิง `fetch` เอง หรือใช้ `curl` จากนอกเบราว์เซอร์
> ก็เรียก API ตรง ๆ ข้ามหน้าจอไปได้เลย โดยไม่ต้องเห็นปุ่มด้วยซ้ำ
> **ซ่อนปุ่ม = ความสะดวก · ตรวจที่เซิร์ฟเวอร์ = ความปลอดภัย** ต้องมีทั้งคู่
> (ท้ายเฟสนี้มีขั้นตอนให้ลองยิงเองด้วย จะได้เห็นว่ามันกันได้จริง)

## 4. `app/users/` — จัดการผู้ใช้

**ขั้นนี้ทำอะไร** ทำ API สามเส้น: ดูรายชื่อผู้ใช้ · สร้างผู้ใช้ใหม่ · แก้ผู้ใช้เดิม
ทั้งสามเส้นเฉพาะ admin

**ก่อนเริ่ม ทำความเข้าใจว่าทำไมแยกเป็น 3 ไฟล์** — ทุกโดเมนในระบบนี้หน้าตาเหมือนกันหมด
(เฟส 3 สินค้า เฟส 4 ใบสั่งซื้อ ก็โครงนี้) จำครั้งเดียวใช้ได้ตลอด:

| ไฟล์ | หน้าที่ | ตอบคำถามว่า |
|---|---|---|
| `schemas.py` | หน้าตาของข้อมูลที่รับเข้า/ส่งออก | "ข้อมูลที่ส่งมาหน้าตาถูกไหม" |
| `service.py` | กฎของธุรกิจ + คุยกับฐานข้อมูล | "ทำได้ไหม ถูกกฎอู่ไหม" |
| `router.py` | ผูก URL เข้ากับฟังก์ชัน + ตรวจสิทธิ์ | "ใครเรียกได้บ้าง" |

ทางเดินของ request หนึ่งครั้งคือ **router → schemas → service → ฐานข้อมูล** แล้วย้อนกลับทางเดิม

ที่แยกเพราะแต่ละชั้นพังคนละแบบ เวลาเทสต์ฟ้อง จะได้รู้ทันทีว่าต้องไปเปิดไฟล์ไหน

**สร้างโฟลเดอร์ `app/users/` ก่อน แล้วสร้างไฟล์ว่างชื่อ `__init__.py` ไว้ข้างใน**
ไฟล์เปล่า ๆ ไม่มีอะไรข้างในเลย — python ใช้มันเป็นเครื่องหมายว่า "โฟลเดอร์นี้ import ได้"
ลืมไฟล์นี้แล้ว `from app.users import service` จะฟ้อง ModuleNotFoundError

### `users/schemas.py` — แก้ import และเติมสอง schema

```python
from pydantic import BaseModel, Field
```

```python
class UserCreate(In):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    full_name: str = Field(min_length=1, max_length=100)
    role: Role
    password: str = Field(min_length=6)


class UserUpdate(In):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6)
```

**อ่านโค้ดนี้ยังไง**

สอง schema นี้คือ "แบบฟอร์ม" ที่ pydantic จะเอาไปตรวจข้อมูลที่ส่งเข้ามา
อะไรไม่ตรงแบบ มันตอบ **422** กลับไปเอง โดยที่โค้ดเราไม่ต้องเขียน `if` สักตัว

`Field(...)` คือเงื่อนไขของช่องนั้น:

```python
username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
#                     ยาว 3-50 ตัว              ^ และต้องเข้ารูปแบบนี้เท่านั้น
```

`pattern` ตัวนั้นอ่านว่า "มีได้แค่ a-z A-Z 0-9 กับ `_` `.` `-` ตั้งแต่ 1 ตัวขึ้นไป"
จงใจไม่ให้ใส่ภาษาไทยและเว้นวรรค เพราะชื่อผู้ใช้คือสิ่งที่ช่างต้องพิมพ์เองทุกเช้า
บนแป้นมือถือ — ภาษาไทยปนเว้นวรรคคือพิมพ์ผิดทุกวัน

**ทำไมต้องมีสองตัว ไม่ใช้ตัวเดียว**

| | `UserCreate` (ตอนสร้าง) | `UserUpdate` (ตอนแก้) |
|---|---|---|
| ทุกช่อง | **บังคับกรอก** | **ไม่บังคับสักช่อง** (`None` ได้หมด) |
| `username` | มี | **ไม่มี** |

- *ตอนแก้ทุกช่องเป็น `None` ได้* เพราะเป็น PATCH = "แก้เฉพาะที่ส่งมา"
  ส่งมาแค่ `full_name` ก็แก้แค่ชื่อ ช่องที่ไม่ส่ง (`None`) แปลว่าไม่แตะ
  ถ้าใช้ schema เดียวกับตอนสร้าง จะกลายเป็นว่าแก้ชื่ออย่างเดียวก็ต้องกรอกรหัสผ่านใหม่ด้วย
- *ตอนแก้ไม่มี `username`* เพราะตั้งใจให้ชื่อผู้ใช้เปลี่ยนไม่ได้เลย
  มันคือสิ่งที่คนจำและพิมพ์ทุกวัน เปลี่ยนทีคนใช้งงทั้งอู่ — ไม่ใส่ช่องนี้ในแบบฟอร์ม
  ก็ปิดประตูตั้งแต่ชั้นนอกสุด ถึงมีคนยิง `username` มาก็ตกไปเฉย ๆ

### `users/service.py` — แก้ import และเติมสองฟังก์ชัน

```python
import os

from fastapi import HTTPException
from sqlalchemy import func, select

from app.auth import hash_password
from app.db import SessionLocal, get_or_404
from app.models import User
```

```python
def create_user(db, data) -> User:
    """กันชื่อผู้ใช้ซ้ำ → hash รหัสผ่าน → บันทึก User ใหม่"""
    if db.scalar(select(User.id).where(User.username == data.username)):
        raise HTTPException(409, "ชื่อผู้ใช้นี้มีแล้ว")
    user = User(
        username=data.username, full_name=data.full_name, role=data.role, password_hash=hash_password(data.password)
    )
    db.add(user)
    db.commit()
    return user


def update_user(db, user_id: int, data, actor: User) -> User:
    """แก้เฉพาะฟิลด์ที่ส่งมา, กัน admin ปิด/ลดสิทธิ์ตัวเอง, มีรหัสใหม่ก็ hash ใหม่"""
    user = get_or_404(db, User, user_id, "ผู้ใช้")
    is_self = user.id == actor.id
    disabling = data.is_active is False
    demoting = data.role is not None and data.role != "admin"
    if is_self and (disabling or demoting):
        raise HTTPException(409, "ปิดหรือลดสิทธิ์บัญชีตัวเองไม่ได้")
    for key, value in data.model_dump(exclude_none=True, exclude={"password"}).items():
        setattr(user, key, value)
    if data.password:
        user.password_hash = hash_password(data.password)
    db.commit()
    return user
```

**อ่าน `create_user`**

บรรทัดแรกเช็คว่าชื่อนี้มีคนใช้แล้วหรือยัง ถ้ามี → 409 พร้อมข้อความไทย

อาจสงสัยว่า *ในเมื่อตาราง `users` มี `unique=True` บน `username` อยู่แล้ว
ฐานข้อมูลก็กันให้อยู่ดี จะเช็คเองทำไมให้ซ้ำซ้อน* — เพราะสองชั้นนี้ทำคนละหน้าที่:

| | กันได้ไหม | ข้อความที่ผู้ใช้เห็น |
|---|---|---|
| เช็คเองใน service | เกือบตลอด | "ชื่อผู้ใช้นี้มีแล้ว" ← คนอ่านรู้เรื่อง |
| `UNIQUE` ที่ฐาน | **100%** | `duplicate key value violates unique constraint...` |

**ชั้นนอกมีไว้ให้ข้อความที่ดี ชั้นในมีไว้ให้ความถูกต้อง** ต้องมีทั้งคู่
(กรณีที่ชั้นนอกหลุดคือสองคนกดสร้างชื่อเดียวกันพร้อมกันเป๊ะ ๆ — ข้อ 6 จะดักไว้ให้)

**อ่าน `update_user` — บรรทัดที่กันอู่พัง**

```python
is_self = user.id == actor.id                                  # กำลังแก้ตัวเองอยู่
disabling = data.is_active is False                            # สั่งปิดบัญชี
demoting = data.role is not None and data.role != "admin"      # สั่งเปลี่ยนเป็นบทบาทอื่นที่ไม่ใช่ admin
if is_self and (disabling or demoting):
```

`actor` คือคนที่กดปุ่ม `user` คือคนที่ถูกแก้ ถ้าเป็นคนเดียวกันและกำลังจะ
ปิดบัญชีตัวเองหรือลดตัวเองเป็นช่าง → ห้าม

**ทำไมแตกเป็นตัวแปรสามตัวที่มีชื่อ** — เงื่อนไขเดียวกันเขียนบรรทัดเดียวได้
(`user.id == actor.id and (data.is_active is False or data.role not in (None, "admin"))`)
แต่ต้องหยุดคิดว่า `not in (None, "admin")` แปลว่าอะไร ตั้งชื่อให้แต่ละท่อนแล้ว
บรรทัด `if` อ่านเป็นประโยคได้เลย: "ถ้าแก้ตัวเอง และ (ปิดบัญชี หรือ ลดสิทธิ์)"

**ทำไมถึงต้องกัน** อู่นี้มี admin คนเดียว ถ้าเขาเผลอปิดบัญชีตัวเอง
จะไม่เหลือใครที่มีสิทธิ์เข้าไปเปิดคืนให้เลย ระบบล็อกตาย
ทางแก้เหลือทางเดียวคือต่อเข้าฐานข้อมูลไปแก้ SQL มือ — ซึ่งเจ้าของอู่ทำไม่ได้แน่นอน

**`is False` ไม่ใช่ `not` — จุดที่พลาดกันบ่อยมาก**

```python
data.is_active is False      # ✅ จริงเฉพาะตอนส่ง false มาจริง ๆ
not data.is_active           # ❌ จริงตอนส่ง false *และ* ตอนไม่ได้ส่งมาเลย (None)
```

เพราะ PATCH ช่องที่ไม่ส่งมาจะเป็น `None` ซึ่ง python ถือว่าเป็น falsy
ถ้าเขียน `not` ปุ๊บ admin จะแก้แม้แต่ชื่อตัวเองไม่ได้เลย เพราะระบบเข้าใจผิดว่ากำลังปิดบัญชีตัวเอง

**`model_dump(exclude_none=True, exclude={"password"})` — "เอาเฉพาะช่องที่ส่งมา ยกเว้นรหัสผ่าน"**

```python
# ส่งมา {"full_name": "สมชาย ใจดี"}   (ช่องอื่นเป็น None)
data.model_dump(exclude_none=True, exclude={"password"})
# → {"full_name": "สมชาย ใจดี"}      แก้แค่ชื่อ ช่องอื่นไม่แตะ
```

- `exclude_none=True` ทิ้งช่องที่เป็น `None` = ช่องที่ไม่ได้ส่งมา → ตรงกับความหมายของ PATCH
- `exclude={"password"}` ทิ้งรหัสผ่านออก เพราะต้อง hash ก่อนเก็บ และคอลัมน์ในตารางชื่อ `password_hash` ไม่ใช่ `password`
  เลยจัดการแยกด้านล่าง

ท่า `for key, value in ...model_dump(...).items(): setattr(...)` เดียวกับ `update_settings` (ข้อ 5) และ `save_product` (เฟส 3)
เห็นท่านี้ที่ไหนให้อ่านว่า "ก๊อปทุกช่องจาก schema ใส่แถวในฐาน"

> **ทำไมไม่มีฟังก์ชันลบผู้ใช้ทิ้ง**
> เอกสารเก่าในระบบบันทึกไว้ว่า "ใบนี้คนนี้เป็นคนทำ" ลบบัญชีทิ้งคือทำลายหลักฐานนั้น
> ใบสั่งซื้อเมื่อปีที่แล้วจะกลายเป็นไม่รู้ว่าใครสั่ง
> ใช้ `is_active = false` แทน — เข้าระบบไม่ได้แล้ว แต่ชื่อยังอยู่ให้อ้างอิงได้
> **กฎนี้ใช้ทั้งระบบ** เฟส 3 สินค้าที่เลิกขายก็ปิดการใช้งาน ไม่ลบเหมือนกัน

### `users/router.py` — ไฟล์ใหม่

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.auth import require_role
from app.db import get_db
from app.models import User
from app.users import service as svc
from app.users.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api", tags=["users"])
admin = require_role("admin")


@router.get("/users", response_model=list[UserOut])
def list_users(db=Depends(get_db), _=Depends(admin)):
    """GET /api/users: admin ดูผู้ใช้ทั้งหมดเรียงตาม id"""
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(data: UserCreate, db=Depends(get_db), _=Depends(admin)):
    """POST /api/users: admin สร้างผู้ใช้ผ่าน svc.create_user"""
    return svc.create_user(db, data)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db=Depends(get_db), actor=Depends(admin)):
    """PATCH /api/users/{id}: admin แก้ชื่อ/role/สถานะ/รหัสผ่าน ผ่าน svc.update_user"""
    return svc.update_user(db, user_id, data, actor)
```

**อ่านโค้ดนี้ยังไง**

สังเกตว่าทุกฟังก์ชันในไฟล์นี้**สั้นมาก** บรรทัดเดียวจบ เพราะหน้าที่ของ router
มีแค่ ตรวจสิทธิ์ → โยนงานให้ service → คืนผล ไม่มีกฎธุรกิจปนอยู่เลย
(ยกเว้น `list_users` ที่แค่อ่านรายการเฉย ๆ ไม่มีกฎอะไร เขียนตรงนี้ได้)

**`admin = require_role("admin")`** บรรทัดบนสุด — สร้างตัวตรวจจากข้อ 3 ไว้ครั้งเดียว
แล้วเอาไปแปะได้ทั้งสามเส้น

**`_` กับ `actor` ต่างกันตรงไหน**

```python
def list_users(db=Depends(get_db), _=Depends(admin)):          # ตรวจแล้วทิ้งค่า
def update_user(..., actor=Depends(admin)):                    # ตรวจแล้วเก็บค่าไว้ใช้
```

ทั้งคู่ตรวจสิทธิ์เหมือนกันเป๊ะ ต่างกันแค่ว่าเอาค่าที่ได้ไปใช้ต่อไหม
- `_` เป็นธรรมเนียมของ python แปลว่า "ต้องรับ แต่ไม่ได้ใช้" — แค่อยากให้มันตรวจ
- `actor` ใน PATCH ต้องใช้จริง เพราะ `update_user` ต้องรู้ว่าใครเป็นคนกด
  ถึงจะเช็คได้ว่ากำลังแก้ตัวเองอยู่หรือเปล่า

**`import service as svc`** — ตั้งชื่อย่อเพราะฟังก์ชันใน service กับฟังก์ชัน endpoint
ตั้งชื่อเดียวกัน (`create_user` ทั้งคู่) เรียกผ่าน `svc.create_user` เลยไม่ชนกัน
และอ่านแล้วรู้ทันทีว่าบรรทัดนี้กำลังข้ามชั้นไปหา service

## 5. `app/settings/` — โดเมนใหม่

**ขั้นนี้ทำอะไร** ทำ API สองเส้นสำหรับค่าตั้งอู่: อ่านค่า กับ บันทึกค่า
โครงเหมือนข้อ 4 ทุกอย่าง (schemas → service → router) แค่เนื้อในสั้นกว่ามาก
ลองอ่านผ่าน ๆ ดูว่าจับรูปแบบได้ไหม

**สร้างโฟลเดอร์ `app/settings/` พร้อม `__init__.py` ว่าง** เหมือนเดิม

### `settings/schemas.py`

```python
from decimal import Decimal

from pydantic import Field

from app.schemas import In, Out


class SettingsIn(In):
    shop_name: str = Field(max_length=200)
    shop_address: str
    shop_tax_id: str = Field(max_length=20)
    vat_rate: Decimal = Field(ge=0, le=100, decimal_places=2)


class SettingsOut(SettingsIn, Out):
    pass
```

**อ่านโค้ดนี้ยังไง**

```python
vat_rate: Decimal = Field(ge=0, le=100, decimal_places=2)
#                         ^ไม่ติดลบ ^ไม่เกิน100  ^ทศนิยมไม่เกิน 2 ตำแหน่ง
```

`decimal_places=2` มีไว้กันเคสเงียบ ๆ: ถ้าใครส่ง `7.12345` มา คอลัมน์ในฐานเป็น
`Numeric(5,2)` มันจะ**ปัดให้เองโดยไม่บอกใคร** กลายเป็น `7.12` — ผู้ใช้เห็นว่าบันทึกสำเร็จ
แต่ค่าที่ได้ไม่ใช่ที่พิมพ์ ใส่บรรทัดนี้แล้วมันตอบ 422 ไปเลยว่าใส่ละเอียดเกิน

**`class SettingsOut(SettingsIn, Out)` — สืบมาสองตัวพร้อมกัน**

- สืบจาก `SettingsIn` → ได้ทุกช่องมาเลย ไม่ต้องพิมพ์ `shop_name`, `vat_rate` ซ้ำอีกรอบ
- สืบจาก `Out` → ได้ `from_attributes=True` ติดมาด้วย ซึ่งแปลว่า
  "แปลงจาก object ของ SQLAlchemy เป็น JSON ได้เลย" router เลย `return row` ตรง ๆ ได้

ขาเข้ากับขาออกหน้าตาเหมือนกันเป๊ะก็เลยเขียนแบบนี้ได้
(ต่างจาก `UserOut` ที่ต้องตัด `password_hash` ทิ้ง เลยประกาศแยก)

### `settings/service.py`

```python
from app.models import Setting


def update_settings(db, data) -> Setting:
    """เขียนทุกฟิลด์จาก data ลงแถว settings id=1 แล้ว commit"""
    row = db.get(Setting, 1)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return row
```

**อ่านโค้ดนี้ยังไง**

`db.get(Setting, 1)` — จำได้ไหมว่าตารางนี้มีแถวเดียว id เป็น 1 เสมอ (ข้อ 2)
เลยหยิบตรง ๆ ได้ ไม่ต้อง query หา ไม่ต้องเช็คว่ามีไหม

`data.model_dump()` แปลง schema เป็น dict ธรรมดา:

```python
{"shop_name": "อู่ช่างเอ", "shop_address": "กรุงเทพฯ", "shop_tax_id": "...", "vat_rate": 7}
```

แล้ว `setattr(row, key, value)` ก็คือ `row.shop_name = "อู่ช่างเอ"` นั่นแหละ
แค่เขียนแบบที่ระบุชื่อช่องตอนรันได้ เลยวน `for` ใส่ทีเดียวจบ

**ที่วนแบบนี้ได้เพราะจงใจตั้งชื่อช่องใน schema ให้ตรงกับชื่อคอลัมน์ในตารางเป๊ะ ๆ**
ผลพลอยได้คือเฟส 6 ที่จะเพิ่มช่อง "วันรับประกันงานซ่อม" เข้ามา
แก้แค่ `models.py` กับ `schemas.py` ฟังก์ชันนี้ไม่ต้องแตะเลย

### `settings/router.py`

```python
from fastapi import APIRouter, Depends

from app.auth import current_user, require_role
from app.db import get_db
from app.models import Setting
from app.settings import service as svc
from app.settings.schemas import SettingsIn, SettingsOut

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings", response_model=SettingsOut)
def get_settings(db=Depends(get_db), _=Depends(current_user)):
    """GET /api/settings: ผู้ใช้ที่ล็อกอิน → คืนค่าตั้งอู่ (แถว id=1) จาก DB"""
    return db.get(Setting, 1)


@router.put("/settings", response_model=SettingsOut)
def update_settings(data: SettingsIn, db=Depends(get_db), _=Depends(require_role("admin"))):
    """PUT /api/settings: admin ส่ง SettingsIn → svc.update_settings → คืนค่าที่บันทึกแล้ว"""
    return svc.update_settings(db, data)
```

**อ่านโค้ดนี้ยังไง — สองเส้นนี้สิทธิ์ไม่เท่ากัน สังเกตบรรทัด `Depends` ให้ดี**

```python
def get_settings(..., _=Depends(current_user)):                 # แค่ล็อกอินก็พอ
def update_settings(..., _=Depends(require_role("admin"))):     # ต้อง admin เท่านั้น
```

**ชื่อ endpoint ตั้งตาม "ทำอะไร" ไม่ใช่ตาม HTTP method** — `update_settings` ไม่ใช่ `put_settings`
อ่านชื่อแล้วรู้เลยว่าเปลี่ยนข้อมูล ชื่อเดียวกับฟังก์ชันใน service ได้เพราะเรียกผ่าน `svc.` ไม่ชนกัน

*อ่านได้ทุกคน* เพราะหน้าจออื่นต้องใช้ชื่ออู่กับอัตรา VAT ไปแสดงผล
(เฟส 4 ใบสั่งซื้อใช้ทั้งคู่) ช่างเปิดดูได้ไม่เสียหายอะไร
*เขียนได้เฉพาะ admin* เพราะแก้ VAT ผิดทีเดียวกระทบบิลทั้งอู่

**ทำไมเส้นนี้เป็น PUT ไม่ใช่ PATCH เหมือนตอนแก้ผู้ใช้**

| | ใช้เมื่อ | ช่องที่ไม่ส่งมา |
|---|---|---|
| `PATCH` | แก้บางช่อง | ไม่แตะ ของเดิมอยู่ครบ |
| `PUT` | แทนทั้งแถว | กลายเป็นค่าว่าง/ค่าที่ส่งมา |

หน้าตั้งค่าเป็นฟอร์มเดียวที่โชว์ทุกช่องพร้อมกัน กดบันทึกทีก็ส่งครบทุกช่องอยู่แล้ว
ใช้ PUT ตรงกับพฤติกรรมจริงมากกว่า และ service ก็เขียนสั้นกว่าเยอะ (ไม่ต้องเช็ค `None` ทีละช่อง)

## 6. `app/main.py` — แทนทั้งไฟล์

**ขั้นนี้ทำอะไร** router ที่เขียนมาทั้งหมดยังไม่มีใครรู้จัก ต้องมาเสียบเข้าแอปตรงนี้
พร้อมกับวาง "ตาข่ายกันพัง" ไว้หนึ่งชั้น

**เปิด** `app/main.py` → ลบของเดิมทิ้งทั้งไฟล์ → วางอันนี้แทน

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.settings import router as settings
from app.users import auth_router as auth
from app.users import router as users
from app.users.service import ensure_admin


@asynccontextmanager
async def lifespan(_app):
    """ตอนเซิร์ฟเวอร์เริ่ม: สร้างบัญชี admin จาก env ถ้ายังไม่มี"""
    ensure_admin()
    yield


app = FastAPI(title="ระบบจัดการอู่ซ่อมรถ", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(settings.router)


@app.exception_handler(IntegrityError)
def handle_integrity_error(_request, _exc):
    """แปลง IntegrityError จาก DB (ชน unique/check) → HTTP 409 ข้อความไทย"""
    return JSONResponse(status_code=409, content={"detail": "ข้อมูลขัดกับกฎของระบบ"})


@app.get("/api/health")
def health():
    """GET /api/health: เช็คว่าเซิร์ฟเวอร์ยังทำงาน"""
    return {"ok": True}
```

**อ่านโค้ดนี้ยังไง**

`app.include_router(...)` สามบรรทัด = เสียบ router ทั้งสามชุดเข้าแอป
หลังบรรทัดนี้ URL อย่าง `/api/users` ถึงจะเรียกได้จริง

**`@app.exception_handler(IntegrityError)` — ตาข่ายชั้นสุดท้าย**

`IntegrityError` คือ exception ที่ SQLAlchemy โยนออกมาเมื่อฐานข้อมูลปฏิเสธข้อมูล
เพราะชนกฎที่ตั้งไว้ที่ฐาน (`UNIQUE`, `CHECK`) — เช่นสองคนกดสร้างชื่อผู้ใช้เดียวกัน
พร้อมกันพอดีจนเช็คใน service ไม่ทัน

**ทำไมเพิ่งมาดักเอาตอนนี้** เพราะเฟสนี้เป็นเฟสแรกที่ผู้ใช้เขียนข้อมูลลงฐานได้
ถ้าไม่ดัก สิ่งที่ผู้ใช้เห็นคือ **500 Internal Server Error พร้อม SQL ดิบ ๆ**
ที่บอกชื่อตาราง ชื่อคอลัมน์ ชื่อ constraint ให้คนนอกรู้โครงสร้างข้างในหมด
ดักแล้วกลายเป็น 409 พร้อมข้อความไทยกลาง ๆ

**ชื่อ `handle_integrity_error`** ขึ้นต้นด้วย `handle_` ให้รู้ว่าเป็น "ตัวจัดการ" error ไม่ใช่ตัว error เอง

ย้ำว่าอันนี้คือชั้น**สุดท้าย** ไม่ใช่ชั้นหลัก — กรณีปกติ service ควรตรวจเจอก่อน
แล้วโยนข้อความที่เจาะจงกว่า ("ชื่อผู้ใช้นี้มีแล้ว") อันนี้มีไว้กันกรณีที่หลุดมาถึงฐานจริง ๆ

## 7. เทสต์

**ขั้นนี้ทำอะไร** เขียนเทสต์ให้ของที่เพิ่งทำเสร็จ โดยเฉพาะ**เรื่องสิทธิ์**

> **ทำไมต้องเทสต์สิทธิ์ทุกกรณี ไม่ใช่แค่ทางที่ถูก**
> บั๊กด้านสิทธิ์เป็นบั๊กชนิดที่ไม่มีใครเจอตอนใช้งานปกติ — พนักงานไม่ได้นั่งลองกด
> ของที่ตัวเองไม่มีสิทธิ์ทุกวัน มันจะโผล่วันที่มีคน*อยากลอง* ซึ่งมักสายไปแล้ว
> เทสต์คือที่เดียวที่เราจะจงใจลองเป็นช่างกดของ admin ดู

### `tests/conftest.py` — เติมบรรทัดเดียวใน `clean`

```python
@pytest.fixture(autouse=True)
def clean(migrated):
    with engine.begin() as conn:
        conn.execute(text(f"truncate {', '.join(Base.metadata.tables)} restart identity cascade"))
        conn.execute(text("insert into settings (id) values (1)"))
```

**ทำไมต้องเติมบรรทัดนี้** — fixture `clean` รันก่อนทุกเทสต์ เพื่อล้างข้อมูลให้เทสต์
แต่ละอันไม่กวนกัน (`autouse=True` แปลว่าไม่ต้องเรียก มันรันให้เอง)

แต่ `truncate` มันล้าง **ทุกแถว** รวมแถวค่าตั้ง id 1 ที่ migration อุตส่าห์ใส่ไว้ด้วย
ไม่ใส่คืน เทสต์ที่แตะค่าตั้งจะพังหมดเพราะ `db.get(Setting, 1)` ได้ `None`

### `tests/test_users.py`

`client` กับ `h` ที่รับเข้ามาคือ fixture จากเฟส 1 — `client` คือตัวยิง request
ส่วน `h` คือ header ที่ล็อกอินไว้แล้วของแต่ละบทบาท เขียน `headers=h["admin"]`
ก็เท่ากับ "ยิงในฐานะ admin"

```python
def test_admin_creates_user_and_duplicate_rejected(client, h):
    body = {"username": "somchai", "password": "secret1", "full_name": "สมชาย", "role": "mechanic"}
    r = client.post("/api/users", json=body, headers=h["admin"])
    assert r.status_code == 201 and "password_hash" not in r.json()
    assert client.post("/api/users", json=body, headers=h["admin"]).status_code == 409


def test_short_password_rejected(client, h):
    body = {"username": "somsri", "password": "123", "full_name": "สมศรี", "role": "employee"}
    assert client.post("/api/users", json=body, headers=h["admin"]).status_code == 422


def test_login_with_created_user_and_password_change(client, h):
    uid = client.post("/api/users", json={"username": "noi", "password": "secret1", "full_name": "น้อย", "role": "employee"},
                      headers=h["admin"]).json()["id"]
    client.patch(f"/api/users/{uid}", json={"password": "secret2"}, headers=h["admin"])
    assert client.post("/api/auth/login", json={"username": "noi", "password": "secret1"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "noi", "password": "secret2"}).status_code == 200


def test_only_admin_manages_users(client, h):
    for role in ("employee", "mechanic"):
        assert client.get("/api/users", headers=h[role]).status_code == 403


def test_admin_cannot_deactivate_or_demote_self(client, h, users):
    url = f"/api/users/{users['admin'].id}"
    assert client.patch(url, json={"is_active": False}, headers=h["admin"]).status_code == 409
    assert client.patch(url, json={"role": "employee"}, headers=h["admin"]).status_code == 409


def test_deactivated_user_token_stops_working(client, h, users):
    client.patch(f"/api/users/{users['employee'].id}", json={"is_active": False}, headers=h["admin"])
    assert client.get("/api/auth/me", headers=h["employee"]).status_code == 401
```

### `tests/test_settings.py`

```python
from app import models
from app.db import SessionLocal

SETTINGS = {"shop_name": "อู่ช่างเอ", "shop_address": "กรุงเทพฯ", "shop_tax_id": "0105555555555", "vat_rate": "7"}


def test_vat_rate_defaults_to_7():
    with SessionLocal() as s:
        assert s.get(models.Setting, 1).vat_rate == 7


def test_settings(client, h):
    r = client.put("/api/settings", json={**SETTINGS, "vat_rate": "10"}, headers=h["admin"])
    assert r.status_code == 200
    assert client.get("/api/settings", headers=h["employee"]).json()["vat_rate"] == "10.00"
    assert client.put("/api/settings", json=SETTINGS, headers=h["employee"]).status_code == 403
    assert client.put("/api/settings", json={**SETTINGS, "vat_rate": "-1"}, headers=h["admin"]).status_code == 422
    assert client.get("/api/settings", headers=h["mechanic"]).json()["shop_name"] == "อู่ช่างเอ"
```

**สรุปรหัสสถานะที่โผล่ในเทสต์พวกนี้** — จำสี่ตัวนี้ไว้ ใช้ยาวทั้งโปรเจกต์

| รหัส | แปลว่า | ใครเป็นคนตอบ | ตัวอย่างในเฟสนี้ |
|---|---|---|---|
| **401** | ยังไม่ได้ล็อกอิน / token ใช้ไม่ได้ | `current_user` | บัญชีถูกปิด แล้ว token เดิมใช้ต่อ |
| **403** | ล็อกอินแล้ว แต่ไม่มีสิทธิ์ | `require_role` | ช่างเรียก `/api/users` |
| **422** | ข้อมูลผิด**รูปแบบ** | pydantic (schemas) | รหัสผ่านสั้นไป, VAT ติดลบ |
| **409** | รูปแบบถูก แต่ขัด**กฎธุรกิจ** | service | ชื่อซ้ำ, ปิดบัญชีตัวเอง |

422 กับ 409 สับสนกันบ่อย — เส้นแบ่งคือ *pydantic ตัดสินได้เองไหมโดยไม่ต้องดูฐานข้อมูล*
"รหัสผ่าน 3 ตัว" ดูแค่ข้อมูลที่ส่งมาก็รู้ว่าผิด → 422
"ชื่อผู้ใช้ซ้ำ" ต้องไปเปิดฐานดูก่อนถึงจะรู้ → 409

**`vat_rate` ที่ได้กลับมาเป็น `"10.00"` ในเครื่องหมายคำพูด ไม่ใช่ `10.0`**

ไม่ใช่บั๊ก — pydantic จงใจส่ง `Decimal` ออกมาเป็น **string** เพราะถ้าส่งเป็นตัวเลข
JSON จะแปลงเป็น float แล้วความแม่นหายไปตั้งแต่ตรงนั้น (ปัญหา `0.1 + 0.2` จากข้อ 2 อีกแล้ว)
ส่วนที่เป็น `.00` ต่อท้ายเพราะค่าที่อ่านจากฐานมีทศนิยม 2 ตำแหน่งตาม `Numeric(5,2)` เสมอ

ฝั่งหน้าจอรับ string นี้ไปใส่ `<input>` ได้เลย ไม่ต้องแปลงอะไร

### รันเทสต์

```
docker compose run --rm api pytest
```

ต้องได้ **passed ทั้งหมด ไม่มี failed** — ตัวเลขจำนวนเทสต์ไม่ต้องตรงกับใคร
ขึ้นกับว่าเขียนไปกี่ตัว (ของเฟสนี้อยู่ราว ๆ 29)

ถ้าแดง อ่านบรรทัดบนสุดของ error ก่อนเสมอ แล้วดูว่าชื่อเทสต์ที่พังอยู่ไฟล์ไหน —
`test_users.py` พัง แปลว่าปัญหาอยู่ในข้อ 4 · `test_settings.py` พัง แปลว่าอยู่ข้อ 2 หรือ 5

---

# ส่วนหน้าจอ

**ส่วนนี้จะได้อะไรบ้าง** ข้อ 8-15 สร้าง**คอมโพเนนต์กลาง** ที่ทุกเฟสหลังจากนี้ใช้ซ้ำ
(ป๊อปอัพ · หน้ารายการ · ป้ายสถานะ · ช่องกรอก) แล้วข้อ 16-21 เอามาประกอบเป็นหน้าจริงสองหน้า

ข้อ 8-15 จะรู้สึกว่า "สร้างของที่ยังไม่รู้จะใช้ทำอะไร" — เป็นเรื่องปกติ
ถ้าอยากเห็นภาพก่อนว่าแต่ละตัวไปโผล่ตรงไหน ข้ามไปอ่านข้อ 18 (`UsersPage.jsx`) ก่อนได้
แล้วค่อยย้อนกลับมา

## 8. `index.css` — เติมคลาสใน `@layer components`

**ขั้นนี้ทำอะไร** เตรียมคลาส CSS ที่คอมโพเนนต์ข้อถัด ๆ ไปจะเรียกใช้
(`.modal`, `.table`, `.badge`, `.tab`) รวมไว้ที่เดียว หน้าตาทั้งระบบจะได้เหมือนกันหมด

ยังไม่ต้องเข้าใจทุกคลาสตอนนี้ — เดี๋ยวเจอตอนใช้จริงจะร้องอ๋อเอง
ข้ามไปทำข้อ 9 ต่อได้เลย แล้วย้อนกลับมาอ่านหัวข้อ "เรื่องที่ควรรู้" ข้างล่างทีหลัง

**เปิด** `frontend/src/index.css` → หาบรรทัด `.label` → เติมใต้มัน

```css
  .field-hint { @apply mt-1 block text-sm text-muted; }
```

→ แล้วหาบรรทัด `.btn-primary` เติมใต้มันอีกชุด

```css
  .btn-secondary { @apply border border-line bg-white text-ink hover:bg-surface; }

  .tabs { @apply flex gap-1 overflow-x-auto border-b border-line; }
  .tab { @apply -mb-px inline-flex min-h-11 cursor-pointer items-center border-b-2 border-transparent px-3 text-sm font-medium whitespace-nowrap text-muted transition-colors duration-150 hover:text-ink aria-selected:border-accent aria-selected:text-ink aria-[current=page]:border-accent aria-[current=page]:text-ink; }

  .modal { @apply mx-0 mt-auto mb-0 max-h-[92dvh] w-full max-w-none rounded-t-2xl bg-white p-0 text-ink backdrop:bg-ink/40 md:m-auto md:max-h-[90dvh] md:w-[calc(100%-2rem)] md:max-w-[560px] md:rounded-xl; }
  .modal[open] { @apply flex flex-col; }

  .table { @apply w-full text-sm; }
  .table th { @apply border-b border-line bg-surface px-3 py-2.5 text-left font-medium whitespace-nowrap text-muted; }
  .table td { @apply border-b border-line px-3 py-3 align-middle; }
  .table tbody tr { @apply cursor-pointer transition-colors duration-150 hover:bg-surface; }

  .badge { @apply inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap; }
  .badge-neutral { @apply bg-neutral-soft text-ink; }
  .badge-info { @apply bg-accent-soft text-accent-ink; }
  .badge-warn { @apply bg-warn-soft text-warn-ink; }
  .badge-ok { @apply bg-ok-soft text-ok-ink; }
  .badge-danger { @apply bg-danger-soft text-danger; }

  .num { font-variant-numeric: tabular-nums; }
```

### เรื่องที่ควรรู้ (กลับมาอ่านทีหลังก็ได้)

**`.modal` — คลาสเดียว หน้าตาสองแบบ**

```
มือถือ                          จอใหญ่ (md: ขึ้นไป)
┌──────────────┐               ┌──────────────┐
│              │               │  ┌────────┐  │
│   (จางลง)    │               │  │ ป๊อปอัพ │  │  ← ลอยกลางจอ
│ ┌──────────┐ │               │  │        │  │    md:m-auto
│ │ ป๊อปอัพ   │ │ ← เลื่อนขึ้น   │  └────────┘  │
└─┴──────────┴─┘   จากขอบล่าง   └──────────────┘
```

บนมือถือทำเป็นแผ่นเลื่อนขึ้นจากล่าง (`mt-auto` + `rounded-t-2xl` มุมบนมน)
เพราะนิ้วโป้งเอื้อมถึงครึ่งล่างของจอ ป๊อปอัพกลางจอบนมือถือกดปิดยาก

**`.badge-*` ใส่ครบห้าสีเลยทั้งที่เฟสนี้ใช้แค่สองสี** เพราะมันคือ*ชุดสีมาตรฐาน*
ที่ทั้งระบบจะยึด กำหนดครั้งเดียวจบ เฟสหลังไม่ต้องมานั่งคิดใหม่ว่าสีไหนแปลว่าอะไร:

| สี | ความหมาย | เจอครั้งแรก |
|---|---|---|
| `ok` เขียว | เรียบร้อย ผ่านแล้ว | เฟสนี้ (ผู้ใช้ที่ยังใช้งานอยู่) |
| `neutral` เทา | จบแล้ว ไม่ต้องทำอะไรต่อ | เฟสนี้ (ผู้ใช้ที่ปิดไปแล้ว) |
| `warn` เหลือง | ต้องทำอะไรสักอย่าง | เฟส 4 |
| `danger` แดง | ยกเลิก / ผิดพลาด | เฟส 4 |
| `info` น้ำเงิน | กำลังดำเนินอยู่ | เฟส 4 |

**`.num` กับ `tabular-nums`** — บังคับให้ตัวเลขทุกตัวกว้างเท่ากัน
ปกติฟอนต์ทำ `1` แคบกว่า `8` พอเรียงเป็นคอลัมน์ราคาแล้วหลักไม่ตรงกัน ตาไล่ยอดยาก
(เฟส 3 เริ่มมีคอลัมน์ตัวเลขเยอะ)

**`.tab` รองรับแท็บสองชนิดด้วยคลาสเดียว** สังเกตว่ามีทั้ง `aria-[current=page]:`
และ `aria-selected:` ในบรรทัดเดียวกัน:

- `aria-current="page"` → `NavLink` ใส่ให้เองเมื่อ URL ตรง (แท็บที่เป็นลิงก์ — ใช้ข้อ 15)
- `aria-selected` → แท็บที่เป็นปุ่มสลับอยู่ในหน้าเดียวกัน ไม่เปลี่ยน URL (เฟส 3 ใช้)

ทั้งคู่วาดขีดใต้แท็บที่ active ด้วย CSS ล้วน — ไม่ต้องเขียน JS เช็คเลยสักบรรทัด

## 9. `components/Icon.jsx` — เติมใน `PATHS`

**ขั้นนี้ทำอะไร** เพิ่มไอคอน 4 ตัวที่เฟสนี้ต้องใช้ ลงในตารางไอคอนจากเฟส 1

**เปิด** `frontend/src/components/Icon.jsx` → หา object ชื่อ `PATHS` → เติมสี่บรรทัดนี้เข้าไป
(ข้างในเป็นพิกัดเส้นของรูป ไม่ต้องอ่านเข้าใจ ก็อปวางได้เลย)

```jsx
  plus: <><path d="M5 12h14" /><path d="M12 5v14" /></>,
  close: <><path d="M18 6 6 18" /><path d="m6 6 12 12" /></>,
  check: <path d="M20 6 9 17l-5-5" />,
  settings: <><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" /></>,
```

## 10. `components/Field.jsx` — ช่องกรอกพร้อมป้าย

**ขั้นนี้ทำอะไร** ทุกช่องกรอกในระบบต้องมี `<label>` ครอบ + คลาสเหมือนกัน
เขียนซ้ำทุกที่เดี๋ยวลืมใส่บ้าง ใส่คลาสผิดบ้าง — รวบเป็นคอมโพเนนต์เดียว

**สร้างไฟล์ใหม่** `frontend/src/components/Field.jsx`

```jsx
// input พร้อม label และ hint, props ที่เหลือส่งต่อให้ <input>
export default function Field({ label, hint, className = "", ...props }) {
  return (
    <label className={`block ${className}`}>
      <span className="label">{label}</span>
      <input className="input" {...props} />
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}
```

**อ่านโค้ดนี้ยังไง**

`{ label, hint, className = "", ...props }` — สามตัวแรกเอาไว้ใช้เอง
ส่วน `...props` คือ "prop อื่น ๆ ที่เหลือทั้งหมด" กวาดรวมไว้ก้อนเดียว
แล้วโยนต่อเข้า `<input {...props} />` ให้หมด

ผลคือใส่อะไรก็ได้ที่ `<input>` ปกติรับ โดยไม่ต้องกลับมาแก้ไฟล์นี้:

```jsx
<Field label="ชื่อ-นามสกุล" required {...register("full_name")} />
<Field label="รหัสผ่าน" type="password" minLength={6} hint="อย่างน้อย 6 ตัว" {...register("password")} />
<Field label="อัตรา VAT (%)" type="number" inputMode="decimal" {...register("vat_rate")} />
```

`required` `type` `minLength` และของที่ `register(...)` คืนมา (`name` `onChange` `onBlur` **`ref`**)
ทั้งหมดนี้ไหลผ่าน `...props` ไปถึง `<input>` ตรง ๆ

> **`ref` ผ่าน `...props` ได้เพราะ React 19** — react-hook-form อ่านค่าจากช่องกรอกผ่าน `ref`
> React รุ่นก่อน 19 ไม่ส่ง `ref` มาใน props ต้องห่อคอมโพเนนต์ด้วย `forwardRef` ถึงจะใช้ `register` ได้
> React 19 ส่งมาเป็น prop ธรรมดาแล้ว `Field` เลยไม่ต้องแก้อะไร ถ้าวันหนึ่ง `register` กับ `Field` แล้วค่าไม่เข้า
> ให้เช็คเวอร์ชัน React ใน `package.json` ก่อน

**ที่ครอบด้วย `<label>` ทั้งก้อนไม่ใช่เรื่องความสวย** — กดที่ข้อความป้ายแล้วเคอร์เซอร์
เด้งเข้าช่องให้เลย (พื้นที่กดใหญ่ขึ้นมาก สำคัญบนมือถือ) และ screen reader
อ่านออกว่าช่องนี้คือช่องอะไร ถ้าแยก `<span>` กับ `<input>` เป็นคนละก้อนจะไม่ได้ทั้งสองอย่าง

> **ทำไมเพิ่งมาแยกเป็นคอมโพเนนต์ตอนนี้ ทำไมไม่ทำตั้งแต่เฟส 1**
> เฟส 1 มีฟอร์มเดียวคือหน้าล็อกอิน เขียนตรง ๆ ในหน้านั้นจบ
> เฟสนี้มีสองฟอร์ม (ผู้ใช้ + ค่าตั้ง) และเฟสหลัง ๆ มีอีกเพียบ
> กฎที่ใช้ทั้งโปรเจกต์คือ **ใช้ 2 ที่ขึ้นไปค่อยแยก** — แยกไว้ก่อนตั้งแต่มีที่เดียว
> มักได้ของที่ไม่พอดีกับที่ที่สอง แล้วต้องรื้ออยู่ดี
> (และหน้า Login เฟส 1 ก็ไม่ต้องกลับไปแก้ ปล่อยไว้แบบนั้นได้ ไม่ได้เสียหายอะไร)

## 11. `components/Modal.jsx` — ป๊อปอัพ

**ขั้นนี้ทำอะไร** ฟอร์มเพิ่ม/แก้ทั้งระบบเปิดเป็นป๊อปอัพทับหน้ารายการ ไม่ใช่เด้งไปอีกหน้า
เพราะผู้ใช้ยังเห็นรายการเดิมเป็นฉากหลัง ไม่หลงว่าตัวเองอยู่ไหน

**สร้างไฟล์ใหม่** `frontend/src/components/Modal.jsx`

```jsx
import { useEffect, useRef } from "react";
import Icon from "./Icon";

// popup จาก <dialog> เปิดทันทีที่ render (อยากปิดก็เลิก render): Esc/คลิกพื้นหลังเรียก onClose, มี onSubmit จะห่อเนื้อหาด้วย <form>
export default function Modal({ title, onClose, onSubmit, footer, children }) {
  const ref = useRef(null);

  useEffect(() => ref.current.showModal(), []);

  const Body = onSubmit ? "form" : "div";
  return (
    <dialog
      ref={ref}
      className="modal"
      aria-label={title}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => e.target === ref.current && onClose()}
    >
      <Body onSubmit={onSubmit} className="flex min-h-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-line py-2 pr-2 pl-4">
          <h2 className="min-w-0 flex-1 truncate text-lg font-semibold">{title}</h2>
          <button type="button" aria-label="ปิด" className="btn btn-ghost btn-icon" onClick={onClose}>
            <Icon name="close" />
          </button>
        </header>
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">{children}</div>
        {footer && (
          <footer className="border-t border-line px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
            {footer}
          </footer>
        )}
      </Body>
    </dialog>
  );
}
```

**กฎเดียวของ Modal: render = เปิด · เลิก render = ปิด**

```jsx
{editing && <ProductModal ... onClose={() => setEditing(false)} />}   // เฟส 3
```

`useEffect(() => ref.current.showModal(), [])` — `[]` ว่าง = รันครั้งเดียวตอนเกิด → เปิดทันที
ไม่มี prop `open` ให้คุม เพราะ**ปิดคือถอดออกจากหน้า** ซึ่งได้ของแถมสำคัญ:
ค่าที่พิมพ์ค้างในฟอร์มหายไปพร้อม Modal เปิดใหม่ครั้งหน้าเริ่มสะอาดเสมอ ไม่ต้องเขียนโค้ดรีเซ็ตฟอร์มเอง

**ทำไมใช้ `<dialog>` ของ HTML แทนที่จะลงไลบรารีป๊อปอัพ**

ป๊อปอัพที่ทำเองด้วย `<div>` ธรรมดา ต้องเขียนเองทุกข้อนี้ และมักลืมข้อใดข้อหนึ่งเสมอ
แต่ `<dialog>` เบราว์เซอร์แถมมาให้ครบตั้งแต่แรก:

| ได้อะไรฟรี | ถ้าทำเองต้องเขียน |
|---|---|
| Tab วนอยู่แต่ในป๊อปอัพ ไม่หลุดไปข้างหลัง | ดักคีย์ Tab + ไล่หา element ที่โฟกัสได้เอง |
| กด Esc แล้วปิด | ดัก keydown เอง |
| ฉากหลังมืด (`::backdrop`) | ทำ overlay div เอง |
| ของข้างหลังกดไม่ได้จริง | ดัก event เอง |
| ลอยบนสุดเสมอ ไม่ต้องสู้กับ `z-index` ใคร | ไล่ตั้ง `z-index` ทั้งโปรเจกต์ |

**สามจุดในโค้ดที่ต้องเข้าใจ (ที่เหลือเป็นแค่โครงหัว-เนื้อ-ท้าย)**

**1. `onCancel` ต้องมี `preventDefault()` — ไม่ใส่แล้วบั๊กประหลาด**

```jsx
onCancel={(e) => { e.preventDefault(); onClose(); }}
//                 ^ ห้าม <dialog> ปิดตัวเอง    ^ แล้วสั่งปิดผ่าน React แทน
```

เพราะ Esc เป็นความสามารถในตัวของ `<dialog>` มันจะปิดตัวเอง **โดยที่ React ไม่รู้เรื่องด้วย**
หน้าข้างนอกยังคิดว่าป๊อปอัพเปิดอยู่ (ยัง render อยู่ แค่มองไม่เห็น) พอกดเปิดครั้งต่อไป
state ไม่ได้เปลี่ยน → ไม่มีอะไร render ใหม่ → ป๊อปอัพเปิดไม่ขึ้นอีกเลย ต้องรีเฟรชหน้า

หลักการคือ **ให้ React เป็นคนคุมสถานะคนเดียว** ห้าม DOM แอบเปลี่ยนเอง

**2. `e.target === ref.current` — วิธีแยก "คลิกฉากหลัง" ออกจาก "คลิกในป๊อปอัพ"**

```
┌─────────────────────────┐
│  ← คลิกตรงนี้ target = <dialog> เอง → ปิด
│    ┌───────────────┐    │
│    │ เนื้อหาป๊อปอัพ  │    │ ← คลิกตรงนี้ target = ลูกข้างใน → ไม่ปิด
│    └───────────────┘    │
└─────────────────────────┘
```

พื้นที่มืด ๆ รอบนอกมันคือตัว `<dialog>` เองในทางเทคนิค เทียบ `target` ทีเดียวก็แยกได้
ไม่ต้องมี div ครอบเพิ่มเป็นชั้น ๆ

**3. `const Body = onSubmit ? "form" : "div"`**

ตัวแปรที่เก็บ *ชื่อ tag* ไว้ แล้วเอาไปเขียนเป็น `<Body>` — React ยอมให้ทำแบบนี้
(ต้องขึ้นต้นด้วยตัวพิมพ์ใหญ่ ไม่งั้น React คิดว่าเป็น tag ชื่อ `body` จริง ๆ)

ป๊อปอัพที่ส่ง `onSubmit` มาจะได้ `<form>` ครอบให้ → กด Enter ในช่องกรอกแล้วบันทึกได้เลย
ป๊อปอัพที่แค่แสดงข้อความได้ `<div>` ธรรมดา ไม่ต้องมี form เปล่า ๆ

**เกร็ดเล็ก ๆ อีกสองอย่าง**

- `min-h-0` ที่เห็นสองที่ — เป็นท่าบังคับของ flexbox เวลาอยากให้ลูกที่เนื้อหายาว
  **เลื่อนในกรอบ** แทนที่จะดันกรอบให้ยืดทะลุจอ (ค่าปริยายของ flex item คือไม่ยอมหดต่ำกว่าเนื้อหา)
- ส่วนใหญ่ในระบบนี้ป๊อปอัพ render เพราะ URL (เดี๋ยวข้อ 13 จะเห็น) — เข้า `/settings/users/new` = render = เปิด
  ออกจาก URL นั้น = เลิก render = ปิด ตรงกับกฎของ Modal พอดี

## 12. `components/DataTable.jsx` — การ์ดบนมือถือ ตารางบนจอใหญ่

**ขั้นนี้ทำอะไร** ทุกหน้ารายการในระบบ (ผู้ใช้ สินค้า ใบสั่งซื้อ…) ต้องแสดงสองแบบ
ตารางบนจอคอม การ์ดบนมือถือ เขียนคอมโพเนนต์นี้ครั้งเดียว ใช้ได้ทุกหน้า

```
มือถือ (แคบ)                      จอใหญ่ (กว้าง ≥ 48rem)
┌────────────────────────┐       ┌───────┬───────┬────────┬─────────┐
│ สมชาย ใจดี     [ใช้งาน] │       │ชื่อผู้ใช้│ ชื่อ   │ บทบาท  │ สถานะ   │
│ mech1 · ช่าง           │       ├───────┼───────┼────────┼─────────┤
├────────────────────────┤       │mech1  │สมชาย  │ ช่าง   │[ใช้งาน] │
│ สมหญิง ขยัน    [ใช้งาน] │       │emp1   │สมหญิง │พนักงาน │[ใช้งาน] │
│ emp1 · พนักงาน         │       └───────┴───────┴────────┴─────────┘
└────────────────────────┘
```

### ก่อนอื่น ดูว่าเวลาเรียกใช้จริงหน้าตาเป็นยังไง

ข้อ 17 จะเขียนหน้า `UsersPage.jsx` แบบนี้ — **ยังไม่ต้องพิมพ์ตอนนี้ แค่ดูให้เห็นภาพ**

```jsx
<DataTable
  items={data}                                    // อาเรย์ที่ได้จาก API
  to={(u) => `/settings/users/${u.id}`}           // กดแถวนี้แล้วไปไหน
  empty="ยังไม่มีผู้ใช้"                             // ข้อความตอนไม่มีข้อมูล
  card={(u) => <div>...</div>}                    // 1 แถวบนมือถือ วาดยังไง
  columns={[                                      // ตารางจอใหญ่ มีคอลัมน์อะไรบ้าง
    { label: "ชื่อผู้ใช้", render: (u) => u.username },
    { label: "บทบาท",   render: (u) => ROLE_NAME[u.role] },
  ]}
/>
```

**จุดสำคัญ: `card` `columns` `to` เป็น _ฟังก์ชัน_ ไม่ใช่ข้อมูล**

`DataTable` ไม่รู้จักคำว่า "ผู้ใช้" เลยสักคำ มันรู้แค่ว่า
"มีของมา n ชิ้น เอาแต่ละชิ้นส่งเข้าฟังก์ชัน `card` แล้วจะได้หน้าตากลับมา"

เฟส 3 เอาไปใช้กับสินค้า ก็แค่ส่ง `card` คนละตัวเข้าไป **ไม่ต้องแก้ไฟล์นี้เลย**

### ทีนี้มาสร้าง

**สร้างไฟล์ใหม่** `frontend/src/components/DataTable.jsx`

```jsx
import { Link, useNavigate } from "react-router-dom";

// แสดง items เป็นการ์ด (แคบ) หรือตาราง (กว้าง), คลิกแถวไปหน้า to(item)
export default function DataTable({ items, columns, card, to, empty = "ไม่มีข้อมูล" }) {
  const navigate = useNavigate();
  if (!items) return <p className="text-muted">กำลังโหลด…</p>;
  if (items.length === 0) return <p className="rounded-xl border border-dashed border-line py-10 text-center text-muted">{empty}</p>;

  // Container query: plain rows until the list is 48rem wide, then a table.
  return (
    <div className="@container">
      <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-white @3xl:hidden">
        {items.map((item) => (
          <li key={item.id}>
            <Link to={to(item)} className="block px-4 py-3 transition-colors duration-150 hover:bg-surface">{card(item)}</Link>
          </li>
        ))}
      </ul>
      <div className="hidden overflow-x-auto rounded-xl border border-line bg-white @3xl:block">
        <table className="table">
          <thead>
            <tr>{columns.map((c) => <th key={c.label} className={c.align === "right" ? "text-right" : ""}>{c.label}</th>)}</tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} onClick={() => navigate(to(item))}>
                {columns.map((c, i) => (
                  <td key={c.label} className={c.align === "right" ? "num text-right" : ""}>
                    {i === 0 ? <Link to={to(item)} className="font-semibold hover:underline">{c.render(item)}</Link> : c.render(item)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

### อ่านโค้ดนี้ยังไง (Tailwind ที่ไม่ได้พูดถึงคือสีกับขอบ ข้ามได้)

**สองบรรทัดบนสุด: สามสถานะต้องครบ**

```jsx
if (!items) return <p>กำลังโหลด…</p>;              // ยังไม่ได้ข้อมูลจาก API (useQuery ให้ data = undefined)
if (items.length === 0) return <p>{empty}</p>;     // ได้แล้ว แต่ว่าง
// ผ่านสองบรรทัดบนมาได้ = มีข้อมูลจริง
```

`!items` (ยังโหลดไม่เสร็จ) กับ `items.length === 0` (โหลดเสร็จแล้วไม่มีข้อมูล)
**เป็นคนละเรื่องกัน** มือใหม่มักเขียนรวมเป็นเงื่อนไขเดียว ผลคือผู้ใช้เห็นหน้าว่าง ๆ
แล้วไม่รู้ว่าเน็ตช้า ระบบพัง หรือไม่มีข้อมูลจริง ๆ

**ท่อนมือถือกับท่อนจอใหญ่ — สลับกันด้วย CSS ล้วน**

```jsx
<ul  className="...        @3xl:hidden">   {/* ปกติโชว์ · กว้าง ≥48rem → ซ่อน */}
<div className="hidden ... @3xl:block">    {/* ปกติซ่อน · กว้าง ≥48rem → โชว์ */}
```

ทั้งสองท่อนวนข้อมูล**ชุดเดียวกัน** แค่วาดคนละแบบ ตัวที่ไม่ตรงขนาดจอถูก CSS ซ่อนทิ้ง
(ไม่ได้ลบออกจากหน้า แค่ไม่แสดง — ง่ายกว่าและไม่กระพริบเวลาหมุนจอ)

**`@container` / `@3xl:` ไม่ใช่ `md:` — ต่างกันตรงไหน**

| | ดูอะไร |
|---|---|
| `md:` (ปกติที่ใช้กัน) | ความกว้างของ**จอ** |
| `@3xl:` (อันนี้) | ความกว้างของ**กล่องที่ตัวเองอยู่ข้างใน** |

ต้องมี `@container` ครอบก่อน ถึงจะวัดได้ว่า "กล่องที่ฉันอยู่กว้างเท่าไหร่"

ทำไมถึงคุ้มกว่า: วันหนึ่งเอารายการนี้ไปวางในคอลัมน์แคบ ๆ ข้างหน้าจอคอม
ถ้าใช้ `md:` มันจะเห็นว่า "จอกว้าง" แล้ววาดตารางอัดจนล้นออกนอกคอลัมน์
แต่ `@3xl:` รู้ว่าที่ที่ตัวเองอยู่มันแคบ เลยเปลี่ยนเป็นการ์ดให้เอง ถูกต้องโดยไม่ต้องแก้อะไร
(`@3xl` = 48rem ≈ 768px)

**คอลัมน์แรกเป็น `<Link>` ทั้งที่ `<tr>` ก็กดได้อยู่แล้ว — ซ้ำซ้อนหรือเปล่า**

ไม่ซ้ำ เพราะสองอันให้คนละอย่าง:

- `onClick` บน `<tr>` → กดตรงไหนของแถวก็ไปได้ สะดวกมือ
- แต่ `onClick` เปล่า ๆ **คลิกขวาเปิดแท็บใหม่ไม่ได้ · กด Tab ไปไม่ถึง ·
  screen reader ไม่รู้ว่ากดได้** เพราะมันไม่ใช่ลิงก์ในสายตาเบราว์เซอร์

ใส่ `<Link>` ที่คอลัมน์แรกด้วย ได้ครบทั้งสองฝั่ง

## 13. `components/ListLayout.jsx` — เปลือกหน้ารายการ

**ขั้นนี้ทำอะไร** หน้ารายการทุกหน้ามีของเหมือนกันหมด: หัวข้อ · ปุ่มเพิ่ม · ตัวรายการ ·
และ**ที่ว่างให้ป๊อปอัพฟอร์มมาเปิดทับ** ข้อนี้ทำเปลือกนั้น

ข้อนี้คือหัวใจของรูปแบบที่ใช้ยาวทั้งโปรเจกต์ อ่านช้า ๆ หน่อย

**สร้างไฟล์ใหม่** `frontend/src/components/ListLayout.jsx`

```jsx
import { Link, useNavigate, useOutlet } from "react-router-dom";
import Icon from "./Icon";

// โครงหน้ารายการ: หัว + ปุ่มเพิ่ม + toolbar + เนื้อหา, ส่ง close() ให้ route ลูก (popup) ผ่าน outlet context
export default function ListLayout({ title, basePath, action, toolbar, children }) {
  const navigate = useNavigate();
  const outlet = useOutlet({ close: () => navigate(basePath) });

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="page-title mr-auto">{title}</h1>
        {action && (
          <Link to={action.to} className="btn btn-primary hidden md:inline-flex"><Icon name="plus" size={20} />{action.label}</Link>
        )}
      </div>
      {toolbar}
      {children}
      {action && (
        <Link to={action.to} aria-label={action.label}
          className="btn btn-primary btn-icon fixed right-4 bottom-6 z-20 size-14 rounded-2xl shadow-lg md:hidden">
          <Icon name="plus" size={28} />
        </Link>
      )}
      {outlet}
    </section>
  );
}
```

### อ่านโค้ดนี้ยังไง

**ของสำคัญที่สุดคือ `useOutlet()` บรรทัดเดียว — "ป๊อปอัพมาจาก URL"**

กฎที่ใช้ทั้งโปรเจกต์คือ **ฟอร์มเพิ่ม/แก้ เป็น route ลูกของหน้ารายการ**

```
/settings/users        → รายการเฉย ๆ
/settings/users/new    → รายการ + ป๊อปอัพ "เพิ่มผู้ใช้" ทับอยู่
/settings/users/5      → รายการ + ป๊อปอัพ "แก้ผู้ใช้ id 5" ทับอยู่
```

จุดที่ต่างจากที่หลายคนคุ้น: `useOutlet()` วาด route ลูก **ทับลงบนรายการ**
ไม่ได้แทนที่รายการ (เพราะเราวาง `{outlet}` ไว้ท้ายสุด *หลัง* `{children}` ที่เป็นตัวรายการ)

**ได้อะไรฟรีจากการผูกป๊อปอัพไว้กับ URL** — เทียบกับทำด้วย `useState` ธรรมดา:

| | ผูกกับ URL (แบบนี้) | `useState` |
|---|---|---|
| กดปุ่ม back ของเบราว์เซอร์ | ปิดป๊อปอัพ ✅ | เด้งออกจากหน้าไปเลย ❌ |
| ส่งลิงก์ให้เพื่อนเปิดฟอร์มตรง ๆ | ได้ ✅ | ไม่ได้ ❌ |
| รีเฟรชหน้า | ฟอร์มยังเปิดอยู่ ✅ | หาย ❌ |

ไม่ต้องเขียนโค้ดเพิ่มสักบรรทัดเพื่อให้ได้สามข้อนี้ — มันมากับการใช้ route

**`useOutlet({ close })` — ส่ง "ปุ่มปิด" ลงไปให้ป๊อปอัพ**

ป๊อปอัพเป็นคนละคอมโพเนนต์ที่อยู่คนละไฟล์ จะส่ง prop ตรง ๆ ไม่ได้
ต้องฝากผ่านตรงนี้ แล้วฝั่งลูกรับด้วย `useOutletContext()` (เห็นในข้อ 19)

`close: () => navigate(basePath)` ให้ป๊อปอัพสั่งปิดตัวเองได้
โดย**ไม่ต้องรู้ว่าตัวเองอยู่ path ไหน** — มันแค่เรียก `close()` ส่วนจะกลับไปหน้าไหน
เป็นเรื่องของ `ListLayout`

**ส่งแค่ `close` ไม่ต้องส่งข้อมูลรายการหรือ `reload` ลงไป** — ป๊อปอัพอยากได้รายชื่อผู้ใช้ก็เรียก
`useQuery({ queryKey: ["users"] })` เอง ได้ของชุดเดียวกับหน้ารายการจาก cache (ไม่ยิงซ้ำ)
บันทึกเสร็จก็ `invalidateQueries({ queryKey: ["users"] })` หน้ารายการข้างหลังอัปเดตเอง
แต่ละไฟล์พึ่งแค่ "กุญแจ" ไม่ต้องรู้จักกันเลย

**ปุ่มเพิ่มมีสองอัน อันไหนโผล่ขึ้นกับขนาดจอ**

```
จอใหญ่                              มือถือ
┌──────────────────────────┐       ┌──────────────┐
│ ผู้ใช้        [+ เพิ่มผู้ใช้]│       │ ผู้ใช้        │
│ ─────────────────────── │       │ ──────────── │
│ (รายการ)                 │       │ (รายการ)      │
│                          │       │         ╭───╮│
└──────────────────────────┘       │         │ + ││ ← นิ้วโป้งถึง
      hidden md:inline-flex        └─────────╰───╯┘    md:hidden
```

ปุ่มบนหัวจอใหญ่กดง่ายด้วยเมาส์ แต่บนมือถือมันอยู่บนสุดของจอ นิ้วโป้งเอื้อมไม่ถึง
เลยย้ายลงมุมล่างขวาแทน (`fixed right-4 bottom-6`)

**`action` ส่ง `false` มาได้ = ไม่มีปุ่มเพิ่มเลย** (`{action && ...}` ข้ามไปทั้งก้อน)
เฟส 3 ใช้ตรงนี้: ช่างเปิดดูรายการสินค้าได้ แต่ไม่เห็นปุ่มเพิ่ม

## 14. `components/StatusBadge.jsx` — ป้ายสถานะ

**ขั้นนี้ทำอะไร** ป้ายสีเล็ก ๆ ที่บอกสถานะ เช่น `[ใช้งาน]` `[ปิดใช้งาน]`

**สร้างไฟล์ใหม่** `frontend/src/components/StatusBadge.jsx`

```jsx
const STATUS = {
  active: ["ใช้งาน", "ok"],
  disabled: ["ปิดใช้งาน", "neutral"],
};

// ป้ายสถานะตาม key ใน STATUS (null = ไม่แสดง)
export default function StatusBadge({ status }) {
  if (!status) return null;
  const [text, t] = STATUS[status];
  return <span className={`badge badge-${t}`}>{text}</span>;
}
```

**อ่านโค้ดนี้ยังไง**

```python
const STATUS = {
  active:   ["ใช้งาน",     "ok"],       // คำที่แสดง, สีที่ใช้
  disabled: ["ปิดใช้งาน",  "neutral"],
};
```

`const [text, t] = STATUS[status]` คือการแกะอาเรย์สองช่องออกมาเป็นสองตัวแปรทีเดียว
แล้วเอา `t` ไปต่อเป็นชื่อคลาส `badge-ok` / `badge-neutral` (สีที่ตั้งไว้ในข้อ 8)

**ทำไมต้องรวมไว้ในตารางเดียวแบบนี้** — สถานะเดียวกันต้องใช้**คำเดียวกันและสีเดียวกัน
ทุกหน้า** ถ้าปล่อยให้แต่ละหน้าเขียนเอง เดี๋ยวหน้าหนึ่งขึ้น "ยกเลิกแล้ว" อีกหน้า "ถูกยกเลิก"
สีก็คนละสี ผู้ใช้เห็นแล้วสงสัยว่ามันคนละอย่างกันหรือเปล่า

เฟสหลัง ๆ มีสถานะใหม่ก็มาเติมทีละแถวที่นี่ที่เดียว

**`if (!status) return null` — ส่ง `null` มาแปลว่าไม่ต้องแสดงป้าย**

คืน `null` ใน React = ไม่วาดอะไรเลย ไม่ใช่ error
มีไว้เพื่อให้หน้าที่ใช้ร่วมกันไม่ต้องเขียน `{x && <StatusBadge .../>}` ครอบทุกที่
(เฟส 3 สินค้าสถานะปกติไม่ต้องมีป้าย มีเฉพาะตอนผิดปกติ)

## 15. `components/SettingsTabs.jsx` — แท็บสลับสองหน้าตั้งค่า

**ขั้นนี้ทำอะไร** หน้าตั้งค่ามีสองหน้า (ตั้งค่าอู่ / ผู้ใช้) ทำแท็บสลับไว้ด้านบน

**สร้างไฟล์ใหม่** `frontend/src/components/SettingsTabs.jsx`

```jsx
import { NavLink } from "react-router-dom";

// แท็บสลับ ตั้งค่าอู่ / ผู้ใช้
export default function SettingsTabs() {
  return (
    <nav aria-label="หมวดตั้งค่า" className="tabs">
      <NavLink to="/settings" end className="tab">ตั้งค่าอู่</NavLink>
      <NavLink to="/settings/users" className="tab">ผู้ใช้</NavLink>
    </nav>
  );
}
```

**อ่านโค้ดนี้ยังไง**

`NavLink` ต่างจาก `Link` ตรงที่มันรู้ตัวว่า "ตอนนี้ URL ตรงกับฉันไหม"
ถ้าตรงมันใส่ `aria-current="page"` ให้เอง → คลาส `.tab` ในข้อ 8 เห็นแล้ววาดขีดใต้ให้

**`end` บนอันแรกสำคัญมาก ลืมแล้วแท็บติดสองอันพร้อมกัน**

ปกติ `NavLink` นับว่า active เมื่อ URL **ขึ้นต้นด้วย** path ของมัน:

```
อยู่ที่ /settings/users
  <NavLink to="/settings">        → /settings/users ขึ้นต้นด้วย /settings → active ❌
  <NavLink to="/settings/users">  → ตรงเป๊ะ → active ✅
                                     ผลคือขีดใต้ขึ้นสองแท็บ
```

ใส่ `end` แปลว่า "ต้องตรงเป๊ะเท่านั้นถึงนับ" — ปัญหาหาย

**ทำไมไฟล์นี้อยู่ใน `components/` ไม่ใช่ `pages/`** เพราะมันถูกใช้สองที่
(หน้าตั้งค่าอู่ ข้อ 17 + หน้าผู้ใช้ ข้อ 18) ตามกฎเดิม: ใช้ 2 ที่ขึ้นไปค่อยแยกออกมา

## 16. `api.js` — เติมตัวตัดศูนย์ท้าย

**ขั้นนี้ทำอะไร** ฐานข้อมูลเก็บ VAT เป็น `Numeric(5,2)` ส่งกลับมาเป็น `"7.00"` เสมอ
ถ้าเอาค่านั้นใส่ช่องกรอกตรง ๆ คนเปิดหน้าตั้งค่าจะเห็น `7.00` ทั้งที่พิมพ์ไว้แค่ `7`

**เปิด** `frontend/src/api.js` → เติมท้ายไฟล์

```js
// ตัดศูนย์ท้ายทิ้งไว้ใส่ช่องกรอก: "150.0000" → "150" (ต่างจาก formatMoney ที่ใส่ , และทศนิยมให้ ซึ่งพิมพ์ต่อไม่ได้)
export const plainNumber = (v) => (v === null || v === undefined || v === "" ? "" : String(Number(v)));
```

`Number("7.00")` ได้ `7` แล้ว `String(7)` ได้ `"7"` — ทั้งหมดที่ต้องทำมีแค่นี้

**ใช้ตอนใส่ค่าลงฟอร์มเท่านั้น ไม่ใช้ตอนแสดงผล** — ของที่แสดงเฉย ๆ ใช้ `formatMoney` (เฟส 3)
ซึ่งใส่คอมมาคั่นหลักให้ (`1,500.00`) เอาไปใส่ช่องกรอกไม่ได้เพราะพิมพ์ต่อแล้วค่าเพี้ยน

| จะเอาเลขไปทำอะไร | ใช้ตัวไหน | ได้ |
|---|---|---|
| ใส่ `<input>` ให้คนแก้ต่อ | `plainNumber` | `150` |
| โชว์เฉย ๆ บนจอ | `formatMoney` (เฟส 3) | `150.00` |

## 17. `pages/SettingsPage.jsx` — หน้าตั้งค่าอู่

**ขั้นนี้ทำอะไร** หน้าจริงหน้าแรกของเฟสนี้ — ฟอร์มกรอกชื่ออู่ ที่อยู่ เลขผู้เสียภาษี VAT
เอาของจากข้อ 8-16 มาประกอบกับ API ข้อ 5 · เป็นหน้าแรกที่ใช้ **`useQuery`** (ดึงข้อมูลมาแสดง)

**สร้างไฟล์ใหม่** `frontend/src/pages/SettingsPage.jsx`

```jsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { api, plainNumber } from "../api";
import Field from "../components/Field";
import Icon from "../components/Icon";
import SettingsTabs from "../components/SettingsTabs";

const GROUPS = [
  [
    "ข้อมูลบนหัวเอกสาร",
    [
      ["shop_name", "ชื่ออู่"],
      ["shop_tax_id", "เลขประจำตัวผู้เสียภาษี"],
      ["shop_address", "ที่อยู่"],
    ],
  ],
  ["ค่าระบบ", [["vat_rate", "อัตรา VAT (%)", "number"]]],
];

// หน้า /settings: GET /settings แล้วส่งค่าให้ SettingsForm
export default function SettingsPage() {
  const { data, error } = useQuery({ queryKey: ["settings"] });

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="page-title">ตั้งค่าและผู้ใช้</h1>
      <SettingsTabs />
      {error && (
        <p role="alert" className="field-error">
          {error.message}
        </p>
      )}
      {data ? <SettingsForm initial={data} /> : !error && <p className="text-muted">กำลังโหลด…</p>}
    </div>
  );
}

// ฟอร์มตั้งค่าอู่: PUT /settings แล้วเอาค่าที่ backend ตอบกลับใส่ cache ["settings"] เลย ไม่ต้องยิง GET ซ้ำ
function SettingsForm({ initial }) {
  const queryClient = useQueryClient();
  const { register, handleSubmit } = useForm({
    defaultValues: { ...initial, vat_rate: plainNumber(initial.vat_rate) },
  });
  const save = useMutation({
    mutationFn: (form) => api("/settings", { method: "PUT", body: form }),
    onSuccess: (saved) => queryClient.setQueryData(["settings"], saved),
  });

  return (
    <form onSubmit={handleSubmit((form) => save.mutate(form))} className="space-y-4">
      {GROUPS.map(([title, fields]) => (
        <section key={title} className="card space-y-4">
          <h2 className="font-semibold">{title}</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {fields.map(([key, label, type]) => (
              <Field
                key={key}
                label={label}
                type={type || "text"}
                inputMode={type ? "decimal" : undefined}
                step="any"
                {...register(key)}
              />
            ))}
          </div>
        </section>
      ))}
      <div className="flex flex-wrap items-center gap-3">
        <button className="btn btn-primary" disabled={save.isPending}>
          {save.isPending ? "กำลังบันทึก…" : "บันทึก"}
        </button>
        {save.error && (
          <span role="alert" className="field-error">
            {save.error.message}
          </span>
        )}
        {save.isSuccess && (
          <span role="status" className="inline-flex items-center gap-1 font-semibold">
            <Icon name="check" size={20} />
            บันทึกแล้ว
          </span>
        )}
      </div>
    </form>
  );
}
```

### อ่านโค้ดนี้ยังไง

**`useQuery({ queryKey: ["settings"] })` — ครั้งแรกที่ใช้ของที่ตั้งไว้ใน `api.js` เฟส 1**

```jsx
const { data, error } = useQuery({ queryKey: ["settings"] });
//      ^ ค่าจากเซิร์ฟเวอร์ (ยังไม่มา = undefined)   ^ กุญแจ = GET /settings
```

ไม่ต้องบอกว่าดึงยังไง เพราะ `queryFn` ตัวกลางใน `api.js` แปลงกุญแจเป็น URL ให้แล้ว
ได้ `data` กับ `error` มาพร้อมใช้ ไม่ต้องมี `useState` / `useEffect` / `try-catch` ของตัวเองเลย

**ทำไมแยกเป็นสองคอมโพเนนต์ (`SettingsPage` กับ `SettingsForm`)**

```
SettingsPage   → ดึงข้อมูล · โชว์ "กำลังโหลด…" / error        ← ไม่มีฟอร์ม
   ↓ ได้ data แล้วค่อย render ↓
SettingsForm   → useForm({ defaultValues: initial })          ← มีฟอร์ม
```

`useForm({ defaultValues })` **อ่านค่าตั้งต้นครั้งเดียวตอนเกิด** — ถ้าเขียนในคอมโพเนนต์เดียวกับ `useQuery`
ตอนเกิด `data` ยังเป็น `undefined` ฟอร์มจะได้ค่าว่างแล้วค้างอยู่อย่างนั้น
แยกแบบนี้ `SettingsForm` เกิด**หลัง**ข้อมูลมาแล้วเท่านั้น (`data ? <SettingsForm .../> : ...`) ได้ค่าถูกตั้งแต่ต้น

ท่านี้ใช้ทั้งโปรเจกต์: **ส่วนดึงข้อมูลอยู่ข้างนอก ฟอร์มอยู่ข้างใน รับ `initial` เป็น prop**

**`GROUPS` — เขียนฟอร์มเป็น*ข้อมูล* แทนที่จะเขียน JSX ซ้ำ ๆ**

```jsx
const GROUPS = [
  ["ข้อมูลบนหัวเอกสาร", [["shop_name", "ชื่ออู่"], ...]],
  ["ค่าระบบ",          [["vat_rate", "อัตรา VAT (%)", "number"]]],
];        //              ^ชื่อคอลัมน์   ^ป้ายที่คนเห็น   ^ชนิดช่อง (ไม่ใส่ = text)
```

แล้วข้างล่างวน `.map()` สองชั้น (กลุ่ม → ช่องในกลุ่ม) วาดออกมาทั้งฟอร์ม

ข้อดีคือเฟส 6 ที่จะเพิ่มช่อง "วันรับประกันงานซ่อม" — เพิ่มแค่หนึ่งแถวในอาเรย์นี้
ไม่ต้องไปแตะ JSX เลย

**`vat_rate: plainNumber(initial.vat_rate)`** — ค่าอื่นใส่ตรง ๆ ได้ (`...initial`) มีแต่ตัวเลขที่ต้องตัดศูนย์ท้ายก่อน
ไม่งั้นช่อง VAT จะขึ้น `7.00` (ข้อ 16)

**`{...register(key)}` — ชื่อคอลัมน์คือชื่อช่องในฟอร์ม**

`key` ใน `GROUPS` ตรงกับชื่อช่องใน `SettingsIn` (backend) และชื่อคอลัมน์ในตาราง
`register("shop_name")` ผูกช่องนี้กับ `form.shop_name` ตอนกดบันทึก `handleSubmit` รวบทุกช่องเป็น
`{ shop_name, shop_tax_id, shop_address, vat_rate }` ส่งเข้า `save.mutate` ครบพอดีกับที่ PUT ต้องการ

**`onSuccess: (saved) => queryClient.setQueryData(["settings"], saved)`**

หลังบันทึกมีสองทางให้ cache ตรงกับฐาน:

| ท่า | ทำอะไร | ใช้เมื่อ |
|---|---|---|
| `invalidateQueries(["settings"])` | บอกว่าเก่าแล้ว → ยิง GET ใหม่ | backend ไม่ได้ส่งของใหม่กลับมา |
| `setQueryData(["settings"], saved)` | เอาของที่ PUT ตอบกลับมา**ใส่แทน**เลย | backend ตอบของใหม่มาทั้งก้อนแล้ว |

PUT `/settings` ตอบ `SettingsOut` กลับมาครบทุกช่อง ใส่ตรง ๆ ได้ ประหยัด request หนึ่งครั้ง
และได้ค่าที่**ฐานเก็บจริง** (พิมพ์ `7` ได้กลับมาเป็น `"7.00"`) — ยืนยันว่าถึงฐานแล้ว

**`save.isSuccess`** — `true` หลังบันทึกสำเร็จ จนกว่าจะกดบันทึกครั้งถัดไป ใช้โชว์ "บันทึกแล้ว ✓" ได้เลย ไม่ต้องมี state เอง

**`inputMode="decimal"`** บนช่อง VAT — สั่งให้มือถือเด้งแป้นตัวเลขที่มีจุดทศนิยมขึ้นมา
แทนแป้นตัวอักษรเต็ม เป็นแค่ความสะดวก ไม่ใช่การตรวจสอบ
ของจริง backend ตรวจซ้ำอยู่แล้ว (`ge=0, le=100, decimal_places=2` จากข้อ 5)

## 18. `pages/UsersPage.jsx` — หน้ารายชื่อผู้ใช้

**ขั้นนี้ทำอะไร** เอา `ListLayout` (ข้อ 13) + `DataTable` (ข้อ 12) + `StatusBadge` (ข้อ 14)
มาประกอบกัน ข้อนี้แทบไม่มีตรรกะอะไรเลย เป็นแค่การต่อจิ๊กซอว์

**นี่คือหน้าตาของหน้ารายการทุกหน้าในระบบ** เฟส 3-4 ก็อปโครงนี้ไปเปลี่ยนแค่ช่อง

**สร้างไฟล์ใหม่** `frontend/src/pages/UsersPage.jsx`

```jsx
import { useQuery } from "@tanstack/react-query";
import { ROLE_NAME } from "../auth";
import ListLayout from "../components/ListLayout";
import DataTable from "../components/DataTable";
import SettingsTabs from "../components/SettingsTabs";
import StatusBadge from "../components/StatusBadge";

// is_active → key ของ StatusBadge
const userStatus = (u) => (u.is_active ? "active" : "disabled");

// หน้า /settings/users: GET /users แสดงรายการ, route ลูกเปิด popup เพิ่ม/แก้ผู้ใช้
export default function UsersPage() {
  const { data, error } = useQuery({ queryKey: ["users"] });
  return (
    <ListLayout
      title="ตั้งค่าและผู้ใช้"
      basePath="/settings/users"
      action={{ label: "เพิ่มผู้ใช้", to: "/settings/users/new" }}
      toolbar={<SettingsTabs />}
    >
      {error && (
        <p role="alert" className="field-error">
          {error.message}
        </p>
      )}
      <DataTable
        items={data}
        to={(u) => `/settings/users/${u.id}`}
        empty="ยังไม่มีผู้ใช้"
        card={(u) => (
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="truncate font-semibold">{u.full_name}</div>
              <div className="text-sm text-muted">
                {u.username} · {ROLE_NAME[u.role]}
              </div>
            </div>
            <StatusBadge status={userStatus(u)} />
          </div>
        )}
        columns={[
          { label: "ชื่อผู้ใช้", render: (u) => u.username },
          { label: "ชื่อ", render: (u) => u.full_name },
          { label: "บทบาท", render: (u) => ROLE_NAME[u.role] },
          { label: "สถานะ", render: (u) => <StatusBadge status={userStatus(u)} /> },
        ]}
      />
    </ListLayout>
  );
}
```

### อ่านโค้ดนี้ยังไง

**โครงของหน้ารายการทุกหน้าในระบบ** — จำรูปนี้ไว้ เจออีกหลายรอบ

```
useQuery({ queryKey: [...] })   ดึงรายการ
<ListLayout>                    เปลือก: หัวข้อ + ปุ่มเพิ่ม + ที่ให้ป๊อปอัพมาเปิด
  <DataTable>                   ตัวรายการ: การ์ด/ตาราง
    card={...}  columns={...}   บอกว่าข้อมูลของหน้านี้วาดยังไง
```

`card` กับ `columns` คือจุดเดียวที่ "ความเป็นหน้าผู้ใช้" อยู่ — ที่เหลือใช้ซ้ำได้หมด

**`card` กับ `columns` แสดงข้อมูลชุดเดียวกัน แต่จัดคนละแบบ**

มือถือที่แคบ ยัดสี่คอลัมน์ไม่ไหว เลยจัดเป็นสองบรรทัดซ้อน + ป้ายชิดขวา:

```jsx
card={(u) => (
  <div className="flex items-center justify-between gap-2">   {/* ซ้าย-ขวา */}
    <div className="min-w-0">
      <div className="truncate font-semibold">{u.full_name}</div>   {/* บรรทัดบน */}
      <div className="text-sm text-muted">{u.username} · {ROLE_NAME[u.role]}</div>
    </div>
    <StatusBadge status={userStatus(u)} />                      {/* ชิดขวา */}
  </div>
)}
```

`truncate` + `min-w-0` คู่นี้แปลว่า "ชื่อยาวเกินให้ตัดเป็น … แทนที่จะดันป้ายตกขอบจอ"
(`min-w-0` จำเป็น เพราะ flex item ปกติไม่ยอมหดต่ำกว่าเนื้อหา — ท่าเดียวกับข้อ 11)

**`userStatus` แปลงข้อมูลดิบเป็นชื่อสถานะ**

```jsx
const userStatus = (u) => (u.is_active ? "active" : "disabled");
```

ฐานข้อมูลเก็บเป็น `true/false` แต่ `StatusBadge` รับเป็นชื่อสถานะ
ทำตัวแปลงไว้ตัวเดียวบนสุด แล้วเรียกใช้ทั้งในการ์ดและในตาราง — คำที่โชว์จะได้ตรงกันแน่ ๆ

**ไม่ได้ส่งอะไรให้ป๊อปอัพเลย** — ป๊อปอัพ `UserFormPage` (ข้อ 19) เรียก `useQuery({ queryKey: ["users"] })` เอง
ได้ข้อมูลชุดเดียวกับหน้านี้จาก cache **ไม่ยิง API ซ้ำ**
และตอนป๊อปอัพบันทึกเสร็จ มันสั่ง invalidate `["users"]` → `useQuery` ของหน้านี้ดึงใหม่เอง รายการข้างหลังอัปเดตทันที

## 19. `pages/UserFormPage.jsx` — ป๊อปอัพเพิ่ม/แก้ผู้ใช้

**ขั้นนี้ทำอะไร** ไฟล์เดียวทำสองงาน: เพิ่มผู้ใช้ใหม่ (`/settings/users/new`)
และแก้ผู้ใช้เดิม (`/settings/users/5`) เพราะฟอร์มหน้าตาเหมือนกันเกือบหมด

**ข้อนี้ยาวและซับซ้อนที่สุดของเฟส** ถ้าอ่านรอบเดียวไม่เข้าใจเป็นเรื่องปกติ
พิมพ์ตามให้ครบก่อน แล้วค่อยกลับมาอ่านคำอธิบายพร้อมกับกดเล่นในจอจริง

**สร้างไฟล์ใหม่** `frontend/src/pages/UserFormPage.jsx` (สะกด `UserFormPage` — `Form` ไม่ใช่ `From`)

```jsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useOutletContext, useParams } from "react-router-dom";
import { api } from "../api";
import { ROLE_NAME } from "../auth";
import Field from "../components/Field";
import Modal from "../components/Modal";

const EMPTY = { username: "", full_name: "", role: "employee", password: "" };

// popup ผู้ใช้ /settings/users/new หรือ /:id: หา user จาก cache ["users"] (ชุดเดียวกับ UsersPage ไม่ยิงซ้ำ) แล้วส่งให้ UserForm
export default function UserFormPage() {
  const { id } = useParams();
  const { close } = useOutletContext();
  const { data: users } = useQuery({ queryKey: ["users"] });
  const current = id && users?.find((u) => String(u.id) === id);
  if (id && !current) return <Modal title={users ? "ไม่พบผู้ใช้" : "กำลังโหลด…"} onClose={close} />;
  return <UserForm key={id ?? "new"} initial={current ? { ...current, password: "" } : EMPTY} close={close} />;
}

// ฟอร์มผู้ใช้: สร้าง POST /users, แก้ PATCH /users/{id}, ปุ่มเปิด/ปิดใช้งาน
function UserForm({ initial, close }) {
  const isEdit = !!initial.id;
  const queryClient = useQueryClient();
  const refreshUsers = () => queryClient.invalidateQueries({ queryKey: ["users"] });
  const { register, handleSubmit } = useForm({ defaultValues: initial });

  const save = useMutation({
    mutationFn: (form) =>
      isEdit
        ? api(`/users/${initial.id}`, {
            method: "PATCH",
            body: { full_name: form.full_name, role: form.role, password: form.password || null },
          })
        : api("/users", { method: "POST", body: form }),
    onSuccess: () => {
      refreshUsers();
      close();
    },
  });

  // สลับ is_active: สถานะที่โชว์มาจาก initial (ข้อมูลใน cache) พอ refresh แล้วจะอัปเดตเอง
  const toggleActive = useMutation({
    mutationFn: () => api(`/users/${initial.id}`, { method: "PATCH", body: { is_active: !initial.is_active } }),
    onSuccess: refreshUsers,
  });

  const busy = save.isPending || toggleActive.isPending;
  const error = save.error ?? toggleActive.error;

  return (
    <Modal
      title={isEdit ? `แก้ไข ${initial.username}` : "เพิ่มผู้ใช้"}
      onClose={close}
      onSubmit={handleSubmit((form) => save.mutate(form))}
      footer={
        <>
          {error && (
            <p role="alert" className="field-error mb-2">
              {error.message}
            </p>
          )}
          <div className="flex gap-2">
            <button className="btn btn-primary flex-1" disabled={busy}>
              บันทึก
            </button>
            {isEdit && (
              <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => toggleActive.mutate()}>
                {initial.is_active ? "ปิดใช้งาน" : "เปิดใช้งาน"}
              </button>
            )}
          </div>
        </>
      }
    >
      {isEdit && <p className="text-sm text-muted">{initial.is_active ? "ใช้งานอยู่" : "ปิดใช้งานแล้ว"}</p>}
      <Field
        label="ชื่อผู้ใช้ (อังกฤษ/ตัวเลข)"
        required
        disabled={isEdit}
        autoCapitalize="none"
        autoComplete="off"
        {...register("username")}
      />
      <Field label="ชื่อ-นามสกุล" required {...register("full_name")} />
      <label className="block">
        <span className="label">บทบาท</span>
        <select className="input" {...register("role")}>
          {Object.entries(ROLE_NAME).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <Field
        label={isEdit ? "รหัสผ่านใหม่" : "รหัสผ่าน"}
        hint={isEdit ? "เว้นว่างถ้าไม่เปลี่ยน · อย่างน้อย 6 ตัว" : "อย่างน้อย 6 ตัว"}
        type="password"
        minLength={6}
        required={!isEdit}
        autoComplete="new-password"
        {...register("password")}
      />
    </Modal>
  );
}
```

### อ่านโค้ดนี้ยังไง

**ทำไมไฟล์เดียวมีสองคอมโพเนนต์ (`UserFormPage` กับ `UserForm`)**

แบ่งหน้าที่กันชัด ๆ (ท่าเดียวกับ `SettingsPage` / `SettingsForm` ข้อ 17):

```
UserFormPage  → หาว่าจะแก้ใคร (อ่าน id จาก URL, หาใน cache ["users"])   ← ไม่มีฟอร์ม
   ↓ ส่ง initial ลงไป
UserForm      → useForm, กดบันทึก, กดปิดใช้งาน                          ← มีฟอร์ม
```

**ถ้ารวมเป็นตัวเดียวจะเจอบั๊กนี้:** `useForm({ defaultValues: initial })` จำค่า**ครั้งแรกที่ถูกสร้าง**เท่านั้น
ค่าที่ส่งเข้ามาทีหลังมันไม่สน ผลคือเปิดฟอร์มแก้คนที่ 5 → ปิด → เปิดแก้คนที่ 8
ฟอร์มยังโชว์ข้อมูลคนที่ 5 อยู่ เพราะฟอร์มยังเป็นก้อนเดิม

**`key={id ?? "new"}` — บรรทัดที่แก้บั๊กนั้น**

`key` เป็นของพิเศษที่ React ใช้ตอบคำถามว่า "ยังเป็นตัวเดิมอยู่ไหม"
พอ key เปลี่ยน (จาก `"5"` เป็น `"8"`) React **ทิ้งตัวเก่าทั้งตัวแล้วสร้างใหม่**
ฟอร์มเก่าหายไปพร้อมกัน ฟอร์มใหม่ได้ค่าเริ่มต้นใหม่ถูกต้อง

นี่คือวิธีมาตรฐานของ React ในการสั่ง "รีเซ็ตคอมโพเนนต์นี้ซะ" — ดีกว่าเขียน
`useEffect` คอยไล่ sync ค่าเอง ซึ่งพลาดง่ายกว่ามาก

(`??` อ่านว่า "ถ้าซ้ายเป็น null/undefined ให้ใช้ขวา" — หน้า `new` ไม่มี id ก็ใช้คำว่า `"new"` เป็น key)

**`useQuery({ queryKey: ["users"] })` ในป๊อปอัพ — ไม่ได้ยิงซ้ำ**

`UsersPage` ข้างหลังขอกุญแจเดียวกันไปแล้ว ข้อมูลอยู่ใน cache ป๊อปอัพได้ของชุดนั้นทันที
และถ้าเปิดลิงก์ `/settings/users/5` ตรง ๆ (cache ยังว่าง) มันยิงให้เอง — ระหว่างรอ `users` เป็น `undefined`
เลยโชว์ Modal "กำลังโหลด…" ก่อน

**`String(u.id) === id` — ต้องแปลงก่อนเทียบ**

```jsx
u.id === id          // ❌ 5 === "5" เป็น false เสมอ ไม่มีวันเจอ
String(u.id) === id  // ✅ "5" === "5"
```

`useParams()` อ่านค่าจาก URL ซึ่งเป็น **string เสมอ** ส่วน `u.id` ที่มาจาก JSON เป็น **number**
`===` ใน JS เทียบชนิดข้อมูลด้วย ต่างชนิดกัน = ไม่ตรงทันที

**สอง mutation ในฟอร์มเดียว: `save` กับ `toggleActive`**

```jsx
const busy = save.isPending || toggleActive.isPending;   // อันไหนกำลังส่ง ปิดทั้งสองปุ่ม
const error = save.error ?? toggleActive.error;          // โชว์ error ของอันที่พัง
```

แยกเป็นสองตัวเพราะส่งของคนละแบบและจบคนละแบบ (ตารางข้างล่าง) แล้วรวม `busy` / `error` ไว้ให้ปุ่มกับข้อความใช้ร่วมกัน

**ปุ่มบันทึกกับปุ่มปิดใช้งาน จบไม่เหมือนกัน — ตั้งใจให้ต่าง**

| | `onSuccess` | เพราะ |
|---|---|---|
| บันทึก | `refreshUsers()` + `close()` ปิดป๊อปอัพ | งานเสร็จแล้ว กลับไปดูรายการต่อ |
| ปิดใช้งาน | `refreshUsers()` อย่างเดียว **ไม่ปิด** | ให้เห็นกับตาว่าสถานะเปลี่ยนเป็น "ปิดใช้งานแล้ว" |

ถ้าปิดใช้งานแล้วป๊อปอัพเด้งหายไปเลย ผู้ใช้จะไม่แน่ใจว่ากดติดหรือเปล่า

**สถานะ "ใช้งานอยู่ / ปิดใช้งานแล้ว" อัปเดตเองได้ยังไง ทั้งที่ไม่มี `setForm`**

```
กดปิดใช้งาน → PATCH สำเร็จ → invalidate ["users"] → useQuery ใน UserFormPage ดึงรายการใหม่
→ current ตัวใหม่ (is_active = false) → ส่งเป็น initial ใหม่ให้ UserForm → ข้อความและปุ่มเปลี่ยน
```

`initial.is_active` อ่านจาก cache ตรง ๆ ไม่ได้เก็บไว้ในฟอร์ม เลยตรงกับฐานเสมอ
(ส่วนช่องที่พิมพ์ค้างไว้ไม่หาย เพราะ `key` ยังเป็นเลขเดิม `UserForm` ไม่ถูกสร้างใหม่ — `useForm` ถือค่าที่พิมพ์ไว้ต่อ)

**`password: form.password || null` — ช่องรหัสผ่านที่เว้นว่างได้**

ตอนแก้ผู้ใช้ ถ้าไม่อยากเปลี่ยนรหัสก็เว้นช่องนี้ว่าง ซึ่งได้ค่าเป็น `""`
แต่ส่ง `""` ไป backend จะตอบ 422 เพราะมันสั้นกว่า `min_length=6`

`|| null` แปลงค่าว่างเป็น `null` ซึ่งใน `UserUpdate` แปลว่า "ไม่แตะช่องนี้" (ข้อ 4)

**ตอนแก้ ส่งแค่ `full_name` `role` `password`** — ไม่ส่ง `username` เพราะ `UserUpdate` ไม่มีช่องนี้ (เปลี่ยนชื่อผู้ใช้ไม่ได้)
และช่อง `username` ก็ `disabled` อยู่บนจอด้วย

**`onClick={() => toggleActive.mutate()}` ไม่ใช่ `onClick={toggleActive.mutate}`** —
เหตุผลเดียวกับ `handleSubmit` ในเฟส 1: `onClick` ส่ง event เป็นตัวแรก ถ้าส่ง `mutate` ตรง ๆ event จะกลายเป็นค่าที่ส่งเข้า `mutationFn`

**`type="button"` บนปุ่มปิดใช้งาน — ลืมใส่แล้วบั๊กเนียนมาก**

ปุ่มที่อยู่ใน `<form>` ถ้าไม่ระบุ `type` เบราว์เซอร์ถือว่าเป็น **submit**
ลืมใส่ปุ๊บ กด "ปิดใช้งาน" จะกลายเป็นกด "บันทึก" แทน — ทำงานผิดแบบที่ไม่มี error ให้เห็นเลย

## 20. ลิงก์ตั้งค่าใน `AppLayout.jsx`

**ขั้นนี้ทำอะไร** หน้าทำเสร็จแล้วแต่ยังไม่มีทางเข้า เพิ่มเมนู "ตั้งค่า" ให้ admin เห็น

**เปิด** `frontend/src/components/AppLayout.jsx` → ในฟังก์ชัน `SidebarContent`
→ เลื่อนลงไปกล่องล่างสุด หาบรรทัด `<div className="px-3 py-2 text-sm">` → เติม**ก่อน**หน้ามัน

```jsx
        {user.role === "admin" && (
          <NavLink to="/settings" className={linkClass}><Icon name="settings" /><span>ตั้งค่า</span></NavLink>
        )}
```

**ทำไมไม่ใส่ในอาเรย์ `MENU` เหมือนเมนูอื่น** — `MENU` คือรายการงานประจำวัน
(งานซ่อม คลัง ฯลฯ) ส่วนตั้งค่าเป็นเรื่องของระบบ นาน ๆ เข้าที
เลยแยกไปอยู่ล่างสุดคู่กับปุ่มออกจากระบบ ไม่ปนกับของที่ใช้ทุกวัน

**`{user.role === "admin" && (...)}`** — คนที่ไม่ใช่ admin จะไม่เห็นเมนูนี้เลย
ย้ำอีกครั้งว่านี่คือ**ความสะดวก ไม่ใช่ความปลอดภัย** ของจริงกันที่ backend ข้อ 3-4 ไปแล้ว

**`className={linkClass}` ไม่ใช่ `className="..."`** — `linkClass` คือฟังก์ชันที่ประกาศไว้
บนสุดของไฟล์ (เฟส 1) `NavLink` จะเรียกมันพร้อมส่ง `{ isActive }` เข้าไปให้เอง
เมนูที่ตรงกับ URL ปัจจุบันจะได้สีเน้น **ส่งชื่อฟังก์ชันเฉย ๆ ห้ามใส่วงเล็บเรียก**

> ถ้าเจอ `ReferenceError: linkClass is not defined` แปลว่าไฟล์ `AppLayout.jsx` ของคุณ
> ตั้งชื่อฟังก์ชันนี้ไว้ต่างจากนี้ เปิดไปดูบรรทัดบน ๆ ของไฟล์ว่าชื่ออะไร แล้วใช้ชื่อนั้นแทน

**เขียนที่เดียวได้สองที่** — `SidebarContent` ถูกเรียกใช้สองครั้งในไฟล์เดียวกัน
ครั้งหนึ่งใน `<nav>` ของแถบข้างจอใหญ่ อีกครั้งใน `<dialog>` ที่เป็นลิ้นชักมือถือ
เติมตรงนี้ทีเดียวขึ้นทั้งสองที่

**ไม่ต้องเขียนโค้ดปิดลิ้นชักหลังกดเมนู** — ตัว `<dialog>` มี `onClick` ที่สั่งปิดตัวเอง
ครอบไว้อยู่แล้ว กดอะไรข้างในมันก็ปิด รวมถึงลิงก์อันนี้ด้วย

## 21. `main.jsx` — เติม import และ route

**ขั้นนี้ทำอะไร** ขั้นสุดท้าย — บอก react-router ว่า URL ไหนวาดหน้าไหน
ก่อนขั้นนี้ พิมพ์ `/settings` จะได้หน้าว่าง เพราะยังไม่มีใครผูกไว้

**เปิด** `frontend/src/main.jsx` → เติม import สามบรรทัดกับ `ADMIN` ไว้บนสุด

```jsx
import SettingsPage from "./pages/SettingsPage";
import UserFormPage from "./pages/UserFormPage";
import UsersPage from "./pages/UsersPage";

const ADMIN = ["admin"];
```

→ แล้วใน layout route หาบรรทัด `<Route path="*" ...>` เติม**ก่อน**หน้ามัน
(`path="*"` ไว้ท้ายสุดเสมอ — react-router เลือก route ที่ตรงที่สุดให้เองไม่ว่าจะเรียงยังไง
แต่คนอ่านไล่จากบนลงล่าง "ที่เหลือทั้งหมด" ควรอยู่ท้าย)

```jsx
            <Route path="settings" element={<Guard roles={ADMIN}><SettingsPage /></Guard>} />
            <Route path="settings/users" element={<Guard roles={ADMIN}><UsersPage /></Guard>}>
              <Route path="new" element={<UserFormPage />} />
              <Route path=":id" element={<UserFormPage />} />
            </Route>
```

**อ่านโครงนี้ยังไง — สังเกตว่า `new` กับ `:id` อยู่*ข้างใน* `settings/users`**

```jsx
<Route path="settings/users" ...>        ← หน้ารายการ
  <Route path="new" ... />               ← ลูก: ป๊อปอัพเพิ่ม
  <Route path=":id" ... />               ← ลูก: ป๊อปอัพแก้
</Route>
```

เขียนซ้อนแบบนี้แหละคือสิ่งที่ทำให้ป๊อปอัพเปิด**ทับ**รายการได้
เพราะ `ListLayout` มี `useOutlet()` ที่คอยวาดลูกไว้ (ข้อ 13) — ถ้าเขียนแยกเป็น route
ระดับเดียวกัน หน้ารายการจะหายไปแล้วขึ้นฟอร์มเต็มจอแทน

`:id` ที่มีโคลอนนำหน้าแปลว่า "ตรงนี้เป็นอะไรก็ได้ เก็บค่าไว้ในชื่อ `id`"
ซึ่งคือค่าที่ `useParams()` ในข้อ 18 ไปอ่านออกมา

**`Guard roles={ADMIN}` ครอบแค่ตัวแม่ ลูกไม่ต้องใส่ซ้ำ** — เข้าตัวแม่ไม่ได้
ก็ไปไม่ถึงลูกอยู่แล้ว

---

## เช็คว่าเฟสนี้เสร็จ

### 1. คำสั่งต้องผ่านทั้งสองอัน

```
docker compose run --rm api pytest
docker compose exec -T web npm run build
```

อันแรกต้อง **passed ทั้งหมด ไม่มี failed** · อันที่สองต้องขึ้น **`✓ built`** ไม่มี error สีแดง

### 2. ลองบนหน้าจอจริง (ล็อกอินเป็น admin)

**สร้างผู้ใช้ไว้ใช้ทดสอบเฟสต่อ ๆ ไป** — ทำครั้งเดียว ใช้ยาว

- สร้าง **`mech1`** บทบาทช่าง และ **`emp1`** บทบาทพนักงาน (รหัสอะไรก็ได้ที่จำได้)

**ผู้ใช้**

- แก้ชื่อผู้ใช้เดิม แล้วกดบันทึกโดย**เว้นช่องรหัสผ่านว่างไว้** → ต้องบันทึกได้ ไม่ฟ้อง
- กดปิดใช้งานผู้ใช้สักคน → ป้ายเปลี่ยนเป็น "ปิดใช้งาน" ทันที **โดยป๊อปอัพไม่ปิด**
- ลองสร้างผู้ใช้ชื่อซ้ำกับที่มีอยู่ → ขึ้นข้อความ "ชื่อผู้ใช้นี้มีแล้ว" ไม่ใช่ error ภาษาอังกฤษ

**ค่าตั้งอู่**

- ตั้งชื่ออู่ และเปลี่ยน VAT เป็น `10` → กดบันทึก → **รีเฟรชหน้า** → ค่ายังอยู่
  (แล้วอย่าลืมตั้งกลับเป็น `7`)

**สิทธิ์ — ข้อนี้สำคัญที่สุดของเฟส**

ล็อกอินใหม่เป็น **`mech1`** แล้วเช็คสามชั้น:

1. เมนูซ้าย → **ไม่เห็น "ตั้งค่า"**
2. พิมพ์ `/settings` ลง URL ตรง ๆ → **เด้งกลับ** ไม่ให้เข้า
3. เปิด DevTools → แท็บ Console → วางอันนี้แล้ว Enter:

```js
fetch("/api/users", {headers: {Authorization: "Bearer " + localStorage.token}}).then(r => r.status)
```

ต้องได้ **`403`** — ข้อ 3 นี่แหละที่พิสูจน์ว่าระบบกันจริง ไม่ใช่แค่ซ่อนปุ่ม
(ถ้าได้ `200` แปลว่า `Depends(admin)` ในข้อ 4 หลุดไปเส้นใดเส้นหนึ่ง กลับไปดู `users/router.py`)

**มือถือ** — ย่อหน้าต่างให้แคบ หรือเปิด DevTools โหมดมือถือ

- ปุ่มเพิ่มผู้ใช้ย้ายไปเป็น**ปุ่มกลมมุมล่างขวา**
- รายการเปลี่ยนจากตารางเป็น**การ์ด**
- ป๊อปอัพ**เลื่อนขึ้นจากขอบล่าง** ไม่ใช่ลอยกลางจอ

**ป๊อปอัพ**

- เปิดป๊อปอัพแล้วกด **Esc** → ปิด
- เปิดใหม่แล้วกด**ปุ่มย้อนกลับของเบราว์เซอร์** → ปิดเหมือนกัน (ไม่ใช่เด้งออกจากหน้า)
- เปิดป๊อปอัพแก้ผู้ใช้ แล้ว**ก็อป URL ไปเปิดแท็บใหม่** → ป๊อปอัพเปิดค้างอยู่เหมือนเดิม

## git

```
docker compose run --rm api ruff check --fix .
docker compose run --rm api ruff format .
docker compose exec -T web npm run format
git add -A && git commit -m "feat: users and shop settings"
```
