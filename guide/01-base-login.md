# เฟส 1 — ฐาน + ล็อกอิน

**จบเฟสนี้แล้วจะทำอะไรได้**

- ล็อกอินด้วยบัญชี admin ที่ตั้งไว้ใน `.env` ได้
- รีเฟรชหน้าแล้วยังล็อกอินอยู่ ไม่หลุด
- ออกจากระบบได้
- จอคอมมีแถบเมนูข้างซ้าย · มือถือกดปุ่ม ☰ แล้วเมนูเลื่อนออกมา

## เฟสนี้ข้อมูลเดินยังไง (อ่าน 1 นาที)

```
คนกรอกชื่อผู้ใช้+รหัสผ่าน
   ↓ หน้าจอส่งไป POST /api/auth/login
backend เปิดตาราง users หาชื่อนี้ แล้วเทียบรหัสผ่านกับ hash ที่เก็บไว้
   ↓ ถูก → ออก "บัตรผ่าน" (token) ส่งกลับ
หน้าจอเก็บบัตรใส่ localStorage ของเบราว์เซอร์
   ↓ ทุกคำขอหลังจากนี้แนบบัตรไปด้วย
backend อ่านบัตร → รู้ว่าใครถาม → ตอบข้อมูลของคนนั้น
```

- **เก็บอะไรในฐาน** ตาราง `users` ตารางเดียว (ชื่อผู้ใช้ · รหัสผ่านที่ hash แล้ว · ชื่อจริง · บทบาท · เปิด/ปิดบัญชี)
- **รหัสผ่านจริงไม่ได้ถูกเก็บ** เก็บแค่ค่าที่คำนวณกลับไม่ได้ ตอนล็อกอินคำนวณใหม่แล้วเทียบ
- **บัตรผ่านมีวันหมดอายุ** หมดแล้วหน้าจอเด้งกลับไปหน้าล็อกอินเอง
- **เปิดเว็บใหม่** หน้าจอเอาบัตรเก่าไปถาม `GET /api/auth/me` ว่า "ยังใช้ได้ไหม ฉันคือใคร"

**อ่านก่อนเริ่ม** `data_model.md` หัวข้อ 1 และหัวข้อ "กฎที่บังคับในฐานข้อมูล"
ถ้านึกภาพไม่ออกว่าไฟล์ไหนต่อกับไฟล์ไหน เปิด [แผนที่ระบบ](01-system-map.md) ไว้อีกจอ

**เฟสนี้ยังไม่ทำ** (ตั้งใจข้าม)

- จัดการผู้ใช้ · ตั้งค่าอู่ · `require_role` — เฟส 2
- `lock_shop` · `money.py` — เฟส 3

ตอนนี้ทั้งระบบมีตารางเดียวคือ `users` เท่านั้น

**ลำดับที่จะทำ** — ทำตามลำดับนี้เท่านั้น เพราะแต่ละขั้นใช้ของจากขั้นก่อนหน้า

```
backend:  db.py → models.py → migration → auth.py → schemas.py → users/ → main.py → เทสต์
หน้าจอ:   index.css → api.js → auth.jsx → Icon → LoginPage → AppLayout → main.jsx
```

---

# ส่วน backend

## 1. `app/db.py` — แทนของเฟส 0 ทั้งไฟล์

**ขั้นนี้ทำอะไร** ตั้งท่อเชื่อมกับฐานข้อมูล ทุกไฟล์ที่ต้องอ่าน/เขียนฐานจะมาหยิบของจากที่นี่

**เปิด** `backend/app/db.py` → ลบของเดิมทิ้งทั้งไฟล์ → วางอันนี้แทน

```python
import os

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

engine = create_engine(os.environ["DATABASE_URL"])
SessionLocal = sessionmaker(engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })
    __mapper_args__ = {"eager_defaults": True}


def get_db():
    """Dependency: เปิด DB session ให้ endpoint แล้วปิดเองเมื่อจบ request"""
    with SessionLocal() as db:
        yield db
```

### อ่านโค้ดนี้ยังไง

ไฟล์นี้สร้างของ 3 อย่างให้คนอื่นเรียกใช้:

| ชื่อ | คืออะไร | ใครใช้ |
|---|---|---|
| `engine` | ท่อเชื่อมฐานข้อมูล มีตัวเดียวทั้งแอป | alembic, เทสต์ |
| `SessionLocal` | โรงงานผลิต "รอบการคุยกับฐาน" หนึ่งรอบ | `get_db()`, สคริปต์ |
| `Base` | คลาสแม่ที่ทุกตารางต้องสืบทอด | `models.py` |

**`os.environ["DATABASE_URL"]` ไม่ใช่ `.get()`** — ต่างกันตรงที่ลืมตั้ง env แล้ว
`[...]` พังทันทีตอนแอปเริ่ม ส่วน `.get()` คืน `None` เงียบ ๆ แล้วไปพังตอนมีคนกดปุ่ม
**อยากให้พังตั้งแต่ต้น ดีกว่าพังตอนลูกค้าใช้อยู่**

**สาม option ของ session ที่ต้องเข้าใจ**

```python
SessionLocal = sessionmaker(engine, autoflush=False, expire_on_commit=False)
```

- `autoflush=False` — ปกติ SQLAlchemy จะแอบเขียนข้อมูลที่ค้างอยู่ลงฐานตอนเราสั่ง
  `select` ปิดไว้แล้วจังหวะการเขียนเป็นของเราคนเดียว ไม่มีอะไรลงฐานโดยไม่ได้สั่ง
- `expire_on_commit=False` — **ไม่ปิดอันนี้จะเจอ error ที่งงมาก** เพราะปกติพอ
  `commit()` เสร็จ SQLAlchemy ถือว่าค่าทั้งหมด "เก่าแล้ว" พอเราแตะ `user.id`
  มันจะวิ่งไป query ฐานใหม่ — ซึ่งตอนนั้น session ปิดไปแล้ว → พัง
- `eager_defaults` (ใน `Base`) — ค่าที่ฐานเติมให้เอง (`created_at`, `is_active`)
  ถูกดึงกลับมาให้ทันทีหลัง insert ไม่ต้อง query ซ้ำ

**`get_db()` ที่ใช้ `yield` ไม่ใช่ `return`**

```python
def get_db():
    with SessionLocal() as db:
        yield db          # ← ส่ง session ให้ endpoint ใช้ แล้วค้างรออยู่ตรงนี้
                          #   พอ endpoint ทำงานเสร็จ with ปิด session ให้เอง
```

FastAPI รู้จักรูปแบบนี้ และจะปิด session ให้เสมอ **ไม่ว่า endpoint จะทำงานสำเร็จ
หรือพังกลางทาง** ถ้าใช้ `return` ธรรมดาจะไม่มีใครปิด session รั่วไปเรื่อย ๆ จนฐานเต็ม

### `naming_convention` — เรื่องที่ดูไม่สำคัญแต่สำคัญมาก

เป็นแม่แบบตั้งชื่อ constraint กับ index ส่วน `%(...)s` คือช่องที่ SQLAlchemy เติมให้เอง

| key | ตัวอย่าง | ชื่อที่ได้ในฐาน |
|---|---|---|
| `pk` primary key | `users.id` | `pk_users` |
| `uq` unique | `users.username` | `uq_users_username` |
| `ck` check | `CheckConstraint(..., name="role")` บน users | `ck_users_role` |
| `fk` foreign key | `stock_lots.product_id` → products (เฟส 3) | `fk_stock_lots_product_id_products` |
| `ix` index | index บน `stock_lots.product_id` | `ix_stock_lots_product_id` |

**ไม่ตั้งก็รันได้** Postgres ตั้งชื่อให้เองตามใจมัน แล้วทำไมต้องตั้ง —
เพราะวันที่ต้อง**แก้** constraint ใน migration เราต้องเรียกมันด้วยชื่อ
ถ้าชื่อมั่วแบบที่ Postgres ตั้ง จะต้องไปเปิดฐานดูทีละอัน (เฟส 4 ต้องแก้ CHECK
ของตาราง Lot จริง ๆ)

> **ต้องตั้งตั้งแต่ก่อนสร้างตารางแรก** — ตั้งทีหลังไม่ช่วยอะไร เพราะของเก่า
> ที่สร้างไปแล้วยังใช้ชื่อเดิม ต้องไล่ rename ทั้งฐาน นี่คือเหตุผลที่ขั้นนี้
> ต้องอยู่ก่อน `models.py`

## 2. `app/models.py` — ตารางแรก

**ขั้นนี้ทำอะไร** ประกาศตาราง `users` — ตารางเดียวของเฟสนี้
เขียนเป็นคลาส python แล้ว SQLAlchemy จะแปลงเป็นตารางจริงในฐานให้

**เปิด** `backend/app/models.py` → แทนทั้งไฟล์

```python
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

TS = DateTime(timezone=True)


def created():
    """คอลัมน์ created_at ที่ DB ใส่เวลาปัจจุบันให้เอง"""
    return mapped_column(TS, server_default=func.now())


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[datetime] = created()
    __table_args__ = (CheckConstraint("role in ('admin','employee','mechanic')", name="role"),)
```

### อ่านโค้ดนี้ยังไง

**วิธีอ่านหนึ่งบรรทัดของคอลัมน์**

```python
username: Mapped[str] = mapped_column(String(50), unique=True)
#         ^ชนิดในฝั่ง python          ^ชนิดในฐาน  ^กฎเพิ่มเติม
```

**`Mapped[str]` ที่ไม่มี `| None` แปลว่า `NOT NULL`** — SQLAlchemy 2 อ่านจาก
type hint ตรงนี้เลย ไม่ต้องเขียน `nullable=False` ซ้ำ

```python
Mapped[str]         # ห้ามว่าง
Mapped[str | None]  # ว่างได้
```

**`TS = DateTime(timezone=True)` ประกาศไว้บนสุด ใช้ทุกคอลัมน์เวลา**

`timezone=True` แปลว่าใช้ `timestamptz` ของ Postgres ซึ่งเก็บเป็น UTC เสมอ

**เวลาที่ไม่มีโซนคือระเบิดเวลา** — เก็บ `02:00` ไว้ แล้ววันหนึ่งมีคนถามว่า
ตีสองของใคร ของไทย ของเซิร์ฟเวอร์ที่ตั้งเป็น UTC หรือของคนที่เปิดดู
ตอบไม่ได้แล้ว เพราะข้อมูลไม่ได้เก็บไว้

เฟสหลังจะมีชนิดกลางแบบเดียวกันเพิ่มอีก (`RATE` เฟส 2 · `MONEY` `PRICE` `QTY` เฟส 3)
หลักการเดียวกันหมด: **ประกาศไว้บนสุดครั้งเดียว ตารางไหนก็ใช้ตัวเดียวกัน**
ตัวเลขทั้งระบบจะได้ไม่เก็บทศนิยมคนละแบบ

**`created()` — ฟังก์ชันที่คืนคอลัมน์**

ทุกตารางในระบบมี `created_at` หน้าตาเหมือนกันเป๊ะ เขียนไว้ครั้งเดียวแล้วเรียกใช้
`created_at: Mapped[datetime] = created()` สั้นกว่าและลืมใส่ `server_default` ไม่ได้

**`CheckConstraint` — ทำไมต้องให้ฐานเช็ค ในเมื่อ python ก็เช็คได้**

```python
CheckConstraint("role in ('admin','employee','mechanic')", name="role")
```

เพราะข้อมูลเข้าฐานได้**หลายทาง** ไม่ใช่แค่ผ่านโค้ดที่เราเขียน:

- migration ที่เขียนผิด
- สคริปต์แก้ข้อมูลที่รันครั้งเดียวแล้วลืม
- คนเปิด `psql` เข้าไปแก้มือ

โค้ด python กันได้แค่ทางเดียว แต่ constraint ที่ฐานกันได้ทุกทาง **กฎไหนที่ฐาน
บังคับได้ ให้ฐานบังคับ** แล้วมันจะจริงตลอดกาลไม่ว่าใครจะเข้ามาทางไหน

ลองพิมพ์ `"Admin"` ตัว A ใหญ่ดู → ฐานปฏิเสธทันที

**`server_default` ต่างจาก `default` ยังไง**

| | ทำงานที่ไหน | ใช้เมื่อ |
|---|---|---|
| `default=True` | ฝั่ง python | insert ผ่านโค้ดเรา |
| `server_default=text("true")` | ในฐานข้อมูลจริง | insert ทางไหนก็ได้ |

`is_active` ใส่ทั้งคู่ เพราะอยากได้ทั้งสองอย่าง — โค้ดเราได้ค่าถูกทันทีโดยไม่ต้อง
query กลับ และแถวที่ใครก็ไม่รู้ insert เข้ามาทางอื่นก็ยังได้ค่าถูก

### สร้าง migration

```
docker compose run --rm api alembic revision --autogenerate -m "users"
```

คำสั่งนี้ไป**เทียบ**ว่าโค้ดใน `models.py` กับฐานข้อมูลจริงต่างกันตรงไหน
แล้วเขียนไฟล์คำสั่งแก้ฐานออกมาให้ใน `backend/alembic/versions/`

**เปิดไฟล์ที่ได้อ่านทุกครั้ง อย่ารันทันที** — ต้องเห็น `op.create_table('users', ...)`
พร้อมชื่อ constraint สามตัวนี้:

```
pk_users              ← primary key
uq_users_username     ← unique
ck_users_role         ← check
```

ชื่อพวกนี้มาจาก `naming_convention` ที่ตั้งไว้ในข้อ 1 **ถ้าเห็นชื่อมั่ว ๆ แทน
แปลว่าข้อ 1 ยังไม่ถูก** ให้ย้อนกลับไปแก้ก่อน แล้วลบไฟล์ migration นี้ทิ้งสร้างใหม่

```
docker compose run --rm api alembic upgrade head
docker compose exec db psql -U garage -d garage -c "\d users"
```

## 3. `app/auth.py` — รหัสผ่านและ token

**ขั้นนี้ทำอะไร** หัวใจของระบบล็อกอินทั้งหมด ทำสามเรื่อง:

```
1. เก็บรหัสผ่าน      hash_password()   รับรหัสจริง → คืนสตริงที่ย้อนกลับไม่ได้
2. ออกบัตรผ่าน       create_token()    ล็อกอินผ่าน → คืน token ให้หน้าจอถือไว้
3. ตรวจบัตรผ่าน      current_user()    รับ token → คืนว่าคนนี้คือใคร
```

**ก่อนเริ่ม: เช็คว่ามี `pwdlib[argon2]>=0.2` ใน `requirements.txt`** (เฟส 0 ใส่ไว้แล้ว)

ถ้าทำเฟส 0 ไปก่อนที่ไฟล์จะมีบรรทัดนี้ ให้เติมแล้ว **build image ใหม่** —
แพ็กเกจ python ถูกอบลง image ตอน build ไม่ได้ติดตั้งตอนรัน แก้ `requirements.txt`
เฉย ๆ แล้วสั่ง `up` จะไม่มีอะไรเปลี่ยน

```
docker compose build api
docker compose up -d
docker compose run --rm api python -c "import pwdlib; print(pwdlib.__version__)"   # ต้องขึ้นเลขเวอร์ชัน
```

**เปิด** `backend/app/auth.py` → แทนทั้งไฟล์

```python
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from pwdlib import PasswordHash

from app.db import get_db
from app.models import User

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_EXPIRE_MINUTES = int(os.environ["JWT_EXPIRE_MINUTES"])

password_hash = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """รับรหัสผ่านดิบ → คืน hash (ใช้ตอนสร้าง/เปลี่ยนรหัสผ่านใน users.service)"""
    return password_hash.hash(password)


def verify_password(password: str, password_hash_value: str) -> bool:
    """เทียบรหัสผ่านที่ผู้ใช้กรอกกับ hash ใน DB → True/False (ใช้ใน /auth/login)"""
    return password_hash.verify(password, password_hash_value)


def create_token(user_id: int) -> str:
    """สร้าง JWT token สำหรับผู้ใช้ที่ระบุ"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode({"user_id": user_id, "exp": expire}, JWT_SECRET, algorithm="HS256")


def current_user(token=Depends(bearer), db=Depends(get_db)) -> User:
    """Dependency: อ่าน Bearer token จาก header → decode JWT → ดึง User จาก DB, ไม่ผ่านโยน 401"""
    user = None
    if token:
        try:
            payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=["HS256"])
            user = db.get(User, payload["user_id"])
        except (jwt.PyJWTError, KeyError):
            pass
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบ")
    return user
```

### อ่านโค้ดนี้ยังไง

ไฟล์เรียงจากบนลงล่างตามลำดับที่ควรอ่าน:

```
ค่าตั้งจาก env  →  ตัวช่วย 2 ตัว  →  รหัสผ่าน  →  สร้าง token  →  ตรวจ token
                  (hasher, ตัวอ่าน header)
```

**ค่าตั้งอ่านครั้งเดียวตอน import** ใช้ `os.environ["..."]` ไม่ใช่ `.get()`
ด้วยเหตุผลเดียวกับข้อ 1 — ลืมตั้ง env แล้วแอปพังตั้งแต่เริ่ม ไม่ใช่ตอนมีคนกดล็อกอิน

> เกร็ดที่จะเจอตอนเขียนเทสต์: `monkeypatch.setenv` เปลี่ยนสองค่านี้ไม่ได้ผล
> เพราะมันถูกอ่านไปตั้งแต่ตอน import แล้ว

### เรื่องรหัสผ่าน

**ทำไมไม่เก็บรหัสผ่านตรง ๆ** — วันที่ฐานข้อมูลหลุด (โดนแฮก · backup หาย ·
พนักงานเก่าเอาไป) รหัสจะหลุดหมดทันที และเพราะคนส่วนใหญ่ใช้รหัสซ้ำกับอีเมล
กับธนาคาร ความเสียหายจะไม่จบแค่ระบบเรา

เก็บเป็น hash แทน = สตริงที่คำนวณกลับเป็นรหัสเดิมไม่ได้ ตอนล็อกอินเอารหัสที่พิมพ์มา
คำนวณใหม่แล้วเทียบว่าได้ค่าเดียวกันไหม

**`PasswordHash.recommended()`** = Argon2id พร้อมค่าตั้งที่แนะนำ ได้สตริงหน้าตาแบบนี้เก็บลง `password_hash`

```
$argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>
  อัลกอริทึม    ค่าตั้ง: หน่วยความจำ 64MB · 3 รอบ · 4 เธรด
```

**`pwdlib` ทำเรื่องที่ต้องระวังให้ครบ — ทั้ง 4 ข้อนี้ถ้าทำเองมักพลาด**

- **salt สุ่มต่อคน** — ถ้า hash เฉย ๆ ไม่มี salt คนที่ได้ฐานไปจะเอาลิสต์
  "รหัสยอดนิยม 10000 อัน" มา hash ครั้งเดียว แล้วเทียบกวาดทั้งตารางได้ในทีเดียว
  salt ทำให้ทุกคนได้ hash ไม่ซ้ำกันแม้ใช้รหัสเดียวกัน → ต้องมานั่งเดาทีละคน
- **ช้าโดยตั้งใจ** — ผู้ใช้รอ ~0.05 วินาทีตอนล็อกอิน ไม่รู้สึกอะไร
  แต่คนที่ไล่เดารหัสต้องเสีย 0.05 วินาทีทุกครั้งที่เดา เดาล้านครั้งคือ 14 ชั่วโมง
- **Argon2 กินหน่วยความจำด้วย** (64MB ต่อครั้ง) — สำคัญเพราะการ์ดจอเดารหัส
  ได้ทีละพันพร้อมกัน แต่ยัด 64MB × 1000 ไม่ไหว ได้เปรียบน้อยกว่าอัลกอริทึม
  ที่กินแค่ CPU อย่าง PBKDF2 มาก
- **ค่าตั้งฝังอยู่ในสตริงเอง** — วันหน้าอยากเพิ่มความแรง รหัสเก่ายังตรวจได้ปกติ
  เพราะแต่ละอันบอกค่าตั้งของตัวเองมาในตัว
- **เทียบแบบใช้เวลาคงที่** — ไม่หยุดทันทีที่เจอตัวอักษรต่าง ป้องกันการเดา
  จากการจับเวลา (timing attack)

**`password_hash = PasswordHash.recommended()` สร้างครั้งเดียวนอกฟังก์ชัน**
ใช้ซ้ำทุก request ไม่ต้องสร้างใหม่

แล้วห่อไว้ในสองฟังก์ชัน `hash_password()` / `verify_password()` เพื่อให้ไฟล์อื่น
ไม่ต้องรู้ว่าข้างในใช้ไลบรารีอะไร — วันหน้าเปลี่ยนไลบรารี แก้ที่ไฟล์นี้ที่เดียวจบ

> **กับดักชื่อชนที่ทำให้ล็อกอินพังทั้งระบบ**
> พารามิเตอร์ตัวที่สองของ `verify_password` **ห้ามตั้งชื่อว่า `password_hash`**
> เพราะมันจะไปบังตัวแปร `password_hash` ที่เป็น hasher ข้างบน
> แล้ว `password_hash.verify(...)` จะกลายเป็นการเรียก `.verify` บน string ธรรมดา
> → `AttributeError` ทุกครั้งที่ล็อกอิน
> นี่คือเหตุผลที่ในโค้ดตั้งชื่อยาว ๆ ว่า `password_hash_value`

**ทำไมไม่ใช้ `passlib` ที่เห็นในบทความเก่า ๆ** — เลิกพัฒนาแล้ว และพังกับ bcrypt
รุ่นใหม่ `pwdlib` คือตัวที่เอกสาร FastAPI แนะนำให้ใช้แทน

### เรื่อง token

**JWT คืออะไรสั้น ๆ** — สตริงที่เซิร์ฟเวอร์เซ็นชื่อกำกับไว้ หน้าจอถือไว้แล้ว
แนบมาทุก request เพื่อบอกว่า "ฉันคือคนที่ล็อกอินไปเมื่อกี้"

**สำคัญ: JWT ใครก็อ่านได้** มันแค่ base64 เอาไปวางใน jwt.io ก็เห็นข้างในหมด
สิ่งที่ลายเซ็นกันได้คือ **แก้ไม่ได้** ไม่ใช่ **อ่านไม่ได้** → ห้ามใส่ความลับลงไป

**ทำไม payload มีแค่ `user_id` กับ `exp` ไม่ใส่ `role` ลงไปด้วย**

ใส่ `role` ลงไปจะเร็วกว่า (ไม่ต้อง query ฐาน) แต่เกิดปัญหานี้:

```
09:00  admin ลดสิทธิ์พนักงานคนหนึ่งจาก admin เป็น employee
09:01  คนนั้นยังใช้ token ใบเดิมที่เขียนว่า role=admin อยู่
21:00  token หมดอายุ ถึงจะเริ่มมีผลจริง        ← ช้าไป 12 ชั่วโมง
```

เก็บแค่ `user_id` แล้ว **โหลดผู้ใช้จากฐานใหม่ทุก request** แทน:
สิทธิ์เปลี่ยนปุ๊บมีผลปั๊บ · ปิดบัญชีปุ๊บเตะออกจากระบบปั๊บ

แลกกับ query เพิ่ม 1 ครั้งต่อ request ซึ่งสำหรับอู่เดียวถือว่าคุ้มมาก

**`user_id` ไม่ใช่ `sub`** — `sub` เป็นชื่อมาตรฐานของ JWT (และต้องเป็น string
ถ้าจะใช้) แต่ token นี้เราเซ็นเองอ่านเองที่เดียว ไม่ได้ส่งให้ระบบอื่น
เลยตั้งชื่อที่อ่านแล้วรู้เรื่องทันที และเก็บเป็นตัวเลขตรง ๆ ไม่ต้องแปลงไปมา

**`exp` ต้องใช้ชื่อนี้เท่านั้น** เพราะเป็นชื่อมาตรฐานที่ PyJWT ตรวจให้เองอัตโนมัติ
หมดอายุแล้ว `decode` จะโยน `ExpiredSignatureError` ออกมาเอง (ซึ่งเป็น
`PyJWTError` ตัวหนึ่ง เลยโดน `except` ข้างล่างดักอยู่แล้ว)

> **`algorithms=["HS256"]` — มี s และเป็น list**
> สะกดเป็น `algorithm` (ไม่มี s) PyJWT จะไม่รู้จักพารามิเตอร์นี้ แล้วโยน
> `DecodeError` ทุกครั้ง ซึ่งโดน `except` ดักกลายเป็น **401 เงียบ ๆ ทุก token**
> ล็อกอินไม่ได้เลยสักคนโดยไม่มี error ให้เห็น — หาสาเหตุยากมาก

**`current_user` — หาผู้ใช้ให้เจอ ไม่เจอด้วยเหตุอะไรก็ตก `raise` จุดเดียว**

```python
user = None                     # เริ่มจาก "ยังไม่รู้ว่าเป็นใคร"
if token:                       # มี header Bearer ถึงค่อยลองอ่าน
    try:
        ...decode แล้ว db.get   # ผ่านหมด user ได้ค่า
    except (...):
        pass                    # token เสีย → user ยังเป็น None
if user is None or not user.is_active:
    raise HTTPException(401, ...)   # ← ทางออกเดียวของทุกกรณีที่ไม่ผ่าน
```

| ทำไม `user` ยังเป็น `None` (หรือใช้ไม่ได้) | เกิดตอนไหน |
|---|---|
| ไม่เข้า `if token` | ไม่มี header `Authorization` หรือไม่ได้ขึ้นต้นด้วย `Bearer` |
| เข้า `except` | token มั่ว · เซ็นด้วย secret อื่น · หมดอายุ · ไม่มี `user_id` |
| `db.get` ได้ `None` | token ถูกแต่ผู้ใช้ถูกลบไปแล้ว |
| `not user.is_active` | token ถูกแต่บัญชีถูกปิด |

**ทำไมเขียนแบบ "ตั้ง `None` ไว้ก่อน" ไม่เขียน `raise` สามที่** — ข้อความ 401 อยู่บรรทัดเดียว วันหน้าจะเปลี่ยนข้อความหรือเพิ่ม log แก้ที่เดียว
และอ่านจากบนลงล่างจบในทางเดียว: "หาผู้ใช้ → ไม่เจอก็ปฏิเสธ"

**ทุกกรณีตอบเหมือนกันหมด: 401 "กรุณาเข้าสู่ระบบ"** — จงใจ ด้วยสองเหตุผล

1. หน้าจอเจอ 401 เมื่อไหร่ก็เด้งไปหน้าล็อกอิน (เขียนไว้ในข้อ 11 `api.js`)
   ไม่ต้องแยกเคส
2. **ไม่บอกใบ้คนที่พยายามเดา** ว่าพลาดตรงไหน — ถ้าตอบต่างกันว่า "ไม่มี token"
   กับ "token หมดอายุ" กับ "ไม่มีผู้ใช้นี้" คนเดาจะรู้ว่าเดาถูกบางส่วนแล้ว

**`auto_error=False` ใน `HTTPBearer(...)`** — ถ้าไม่ปิด ค่าเริ่มต้นของมันคือ
โยน error ภาษาอังกฤษรูปแบบของมันเองตอนไม่มี header ซึ่งไม่ตรงกับข้อความไทย
ของเรา ปิดแล้วมันคืน `None` มาให้เราเช็คเองที่ `if token:` แทน

**docstring บรรทัดเดียวใต้ทุกฟังก์ชัน** (กติกาจากเฟส 0) — อ่านแค่บรรทัดนั้นก็รู้ว่ารับอะไร คืนอะไร ใครเรียก
เช่น `hash_password` บอกไว้เลยว่า "ใช้ตอนสร้าง/เปลี่ยนรหัสผ่านใน users.service" ไม่ต้องไล่ grep

## 4. `app/schemas.py` — ของกลางที่ทุกโดเมนใช้

**ขั้นนี้ทำอะไร** ประกาศคลาสแม่สองตัวที่ schema ทุกตัวในระบบจะสืบทอดต่อ
เพื่อไม่ต้องตั้งค่าเดิมซ้ำทุกไฟล์

**สร้างไฟล์ใหม่** `backend/app/schemas.py` (ไม่ใช่โฟลเดอร์ เป็นไฟล์เดี่ยว)

```python
from pydantic import BaseModel, ConfigDict


class In(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True
    )


class Out(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )
```

### อ่านโค้ดนี้ยังไง

สองคลาสนี้ไม่มีช่องข้อมูลอะไรเลย มีแต่ **การตั้งค่า** ที่อยากให้ลูกทุกตัวได้ไปด้วย

**`In` — คลาสแม่ของ schema ขาเข้าทุกตัว**

`str_strip_whitespace=True` ตัดช่องว่างหัวท้ายของทุกช่องที่เป็นข้อความให้อัตโนมัติ

```
คนพิมพ์  "somchai "   ← เผลอเคาะ space ท้าย
เก็บจริง  "somchai"
```

ถ้าไม่ตัด มันจะกลายเป็นคนละชื่อกับ `"somchai"` แล้วล็อกอินไม่ได้โดยไม่รู้สาเหตุ

**`Out` — คลาสแม่ของ schema ขาออกที่อ่านค่าจาก object ของ SQLAlchemy**

`from_attributes=True` อนุญาตให้ pydantic อ่าน `user.username` จาก object ตรง ๆ

```python
return user          # ✅ ทำแบบนี้ได้เลย
return {"username": user.username, ...}    # ❌ ไม่ต้องแปลงเองแบบนี้
```

ประกาศไว้ที่นี่ที่เดียว ทุกไฟล์ที่สืบจาก `Out` ได้ไปด้วย ไม่ต้องพิมพ์
`model_config` ซ้ำในทุกคลาส

**ตารางตัดสินใจ — เขียน schema ใหม่เมื่อไหร่ให้สืบจากอะไร**

| schema แบบไหน | สืบจาก | ตัวอย่าง |
|---|---|---|
| ขาเข้า (รับข้อมูลจากหน้าจอ) | `In` | `LoginIn`, `UserCreate` |
| ขาออก ที่ `return` object จากฐานตรง ๆ | `Out` | `UserOut` |
| ขาออก ที่อยากได้ช่องเหมือนขาเข้าเป๊ะ | **ทั้งสองตัว** | `class SettingsOut(SettingsIn, Out)` |
| ขาออก ที่เราประกอบ dict เอง | `BaseModel` เฉย ๆ | `LoginOut` |

> แถวที่สามคือแถวที่พลาดบ่อย — **ลืมใส่ `Out` แล้วจะอ่านจาก object ไม่ได้ → 500**
> pydantic รวม config จากแม่ทั้งสองตัวให้เอง ใส่ไปทั้งคู่ได้เลย

ไฟล์นี้จะโตขึ้นเรื่อย ๆ ตามเฟส: `serialize_for_role` (เฟส 3) · `ReasonIn` (เฟส 4)

## 5. โดเมน `users/`

**ขั้นนี้ทำอะไร** ทำ API สองเส้น: `POST /api/auth/login` (ล็อกอิน) และ
`GET /api/auth/me` (ถามว่าฉันคือใคร) พร้อมสร้างบัญชี admin คนแรกให้อัตโนมัติ

**โครง 3 ไฟล์ที่ใช้ทุกโดเมนทั้งโปรเจกต์** — จำครั้งเดียวใช้ได้ตลอด

| ไฟล์ | หน้าที่ | ตอบคำถามว่า |
|---|---|---|
| `schemas.py` | หน้าตาข้อมูลเข้า/ออก | "ข้อมูลที่ส่งมาถูกรูปแบบไหม" |
| `service.py` | กฎธุรกิจ + คุยกับฐาน | "ทำได้ไหม ถูกกฎไหม" |
| `router.py` | ผูก URL กับฟังก์ชัน | "ใครเรียกได้บ้าง" |

ทางเดินของ request: **router → schemas → service → ฐานข้อมูล** แล้วย้อนกลับทางเดิม

**สร้างโฟลเดอร์ `backend/app/users/` พร้อมไฟล์เปล่าชื่อ `__init__.py` ข้างใน**
ไฟล์นี้ไม่มีอะไรข้างในเลย python ใช้มันเป็นเครื่องหมายว่าโฟลเดอร์นี้ import ได้
ลืมไฟล์นี้แล้ว `from app.users import ...` จะหาไม่เจอ

### `app/users/schemas.py`

```python
from typing import Literal

from pydantic import BaseModel

from app.schemas import In, Out

Role = Literal["admin", "employee", "mechanic"]


class UserOut(Out):
    id: int
    username: str
    full_name: str
    role: Role
    is_active: bool


class LoginIn(In):
    username: str
    password: str


class LoginOut(BaseModel):
    access_token: str
    user: UserOut
```

**อ่านโค้ดนี้ยังไง**

**`UserOut` ไม่มีช่อง `password_hash` — นี่คือด่านกันรหัสผ่านรั่ว**

pydantic จะส่งออกเฉพาะช่องที่ประกาศไว้เท่านั้น ช่องที่ไม่ได้ประกาศถูกตัดทิ้งเงียบ ๆ
แปลว่าต่อให้ router เขียน `return user` คืน object ทั้งก้อนที่มี `password_hash`
อยู่ข้างใน มันก็ไม่หลุดออกไปถึงหน้าจอ

**`Role = Literal["admin", "employee", "mechanic"]`**

`Literal` แปลว่า "เป็นได้แค่ค่าใดค่าหนึ่งในนี้เท่านั้น" ส่งค่าอื่นมา → 422

สังเกตว่ามันซ้ำกับ `CheckConstraint` ที่ตั้งไว้ในฐาน (ข้อ 2) — **ตั้งใจให้ซ้ำ**
ด้วยเหตุผลเดียวกับเรื่องชื่อผู้ใช้ซ้ำ: pydantic ปฏิเสธที่ขอบนอกพร้อมข้อความ
ที่คนอ่านรู้เรื่อง · CHECK ที่ฐานเป็นตาข่ายชั้นสุดท้ายที่ไม่มีทางหลุด

**สามคลาสสืบจากคนละที่ ไม่ได้สุ่ม**

```python
class UserOut(Out):        # return ORM object ตรง ๆ ได้ → ต้องมี Out
class LoginIn(In):         # รับข้อมูลเข้า → ต้องมี In (ตัดช่องว่างให้)
class LoginOut(BaseModel): # router ประกอบ dict เอง → ไม่ต้องใช้อะไรพิเศษ
```

แถวสุดท้ายอาจงง: `LoginOut` มีช่อง `user` ที่เป็น `UserOut` ซึ่งข้างในเป็น
ORM object — อ่านได้ไหม **ได้** เพราะ `UserOut` เป็น `Out` อยู่แล้ว
ตัวห่อข้างนอกไม่ต้องเป็นก็ได้

### `app/users/service.py`

```python
import os

from sqlalchemy import func, select

from app.auth import hash_password
from app.db import SessionLocal
from app.models import User


def ensure_admin():
    """ตารางผู้ใช้ยังว่าง → สร้าง admin คนแรกจาก env ADMIN_USERNAME/ADMIN_PASSWORD (เรียกจาก lifespan)"""
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(User)) == 0:
            db.add(User(username=os.environ["ADMIN_USERNAME"], full_name="ผู้ดูแลระบบ", role="admin",
                        password_hash=hash_password(os.environ["ADMIN_PASSWORD"])))
            db.commit()
```

**ปัญหาไก่กับไข่ที่ฟังก์ชันนี้แก้** — ระบบที่เพิ่งติดตั้งใหม่ไม่มีผู้ใช้สักคน
แปลว่าไม่มีใครล็อกอินได้ แปลว่าไม่มีใครสร้างผู้ใช้ได้ ตันตั้งแต่ยังไม่เริ่ม

ทางออกคือให้แอปสร้าง admin คนแรกให้เองตอนเริ่มทำงาน โดยอ่านชื่อกับรหัสจาก `.env`

**ทำไมเช็ค "ไม่มีผู้ใช้เลยสักคน" ไม่ใช่ "ไม่มี admin ชื่อนี้"**

```python
if db.scalar(select(func.count()).select_from(User)) == 0:    # ✅ ทั้งตารางว่าง
# if ไม่มี user ที่ username == ADMIN_USERNAME:               # ❌ อย่าทำ
```

เพราะแบบหลัง วันที่เจ้าของอู่ปิดหรือลบบัญชี admin ตั้งต้นทิ้ง มันจะ**โผล่กลับมาใหม่
ทุกครั้งที่รีสตาร์ท** กลายเป็นบัญชีลับที่ปิดไม่ได้ — ซึ่งเป็นช่องโหว่ความปลอดภัย

แบบที่ใช้จะทำงานแค่ครั้งเดียวจริง ๆ ตอนระบบยังว่างเปล่า

**ทำไมเปิด session เองด้วย `with SessionLocal()` ไม่รับ `db` เข้ามาแบบฟังก์ชันอื่น**

เพราะฟังก์ชันนี้ถูกเรียกตอน**แอปเริ่มทำงาน** ซึ่งยังไม่มี request เข้ามาเลย
ไม่มี `Depends` ให้ใช้ ต้องจัดการ session เอง

> **กฎเหล็กของโปรเจกต์นี้: `service.py` คือทางเดียวที่เขียนข้อมูลลงฐานได้**
> router ห้ามมี `db.add` / `db.commit` เด็ดขาด
> เพราะถ้าโค้ดที่เขียนฐานกระจายอยู่หลายที่ วันที่กฎธุรกิจเปลี่ยน
> (เช่น "ทุกครั้งที่สร้างผู้ใช้ต้องบันทึก log ด้วย") จะแก้ไม่ครบแน่นอน
> ข้อยกเว้นเดียวคือ**การอ่าน** — `select` เฉย ๆ เขียนใน router ได้

### `app/users/auth_router.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.auth import create_token, current_user, verify_password
from app.db import get_db
from app.models import User
from app.users.schemas import LoginIn, LoginOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(data: LoginIn, db=Depends(get_db)):
    """POST /api/auth/login: รับ username/password → เช็คกับ DB → คืน JWT + ข้อมูลผู้ใช้"""
    user = db.scalar(select(User).where(User.username == data.username))
    if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    return {"access_token": create_token(user.id), "user": user}


@router.get("/me", response_model=UserOut)
def me(user=Depends(current_user)):
    """GET /api/auth/me: คืนข้อมูลผู้ใช้เจ้าของ token (frontend ใช้ตอนเปิดแอป)"""
    return user
```

**อ่านโค้ดนี้ยังไง**

**ทำไมชื่อไฟล์เป็น `auth_router.py` ไม่ใช่ `router.py` เฉย ๆ**

เพราะ prefix ของ URL คนละตัวกัน — อันนี้เป็น `/api/auth` ส่วนเฟส 2 จะมี
`router.py` ที่เป็น `/api/users` แต่ทั้งคู่เป็นเรื่องของผู้ใช้เหมือนกัน
เลยอยู่โฟลเดอร์เดียวกันได้

**`login` เขียน query ใน router ได้ ไม่ผิดกฎข้อเมื่อกี้** เพราะมันแค่**อ่าน**
ไม่มี `db.add` / `db.commit` สักตัว

**เงื่อนไขเดียวยาว ๆ ที่รวมสามกรณี**

```python
if user is None or not user.is_active or not verify_password(...):
#  ไม่มีชื่อนี้      บัญชีถูกปิด        รหัสผิด
    raise HTTPException(401, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
```

**ทั้งสามกรณีตอบข้อความเดียวกันเป๊ะ — ตั้งใจ** ถ้าแยกข้อความเป็น
"ไม่พบชื่อผู้ใช้นี้" กับ "รหัสผ่านไม่ถูกต้อง" คนนอกจะยิงลองชื่อไปเรื่อย ๆ
แล้วรู้ได้ว่าบัญชีไหนมีอยู่จริงในระบบ (เรียกว่า user enumeration)

**`GET /auth/me` มีไว้ทำไม ในเมื่อ login ก็คืนข้อมูลผู้ใช้มาแล้ว**

เพราะหน้าเว็บเก็บ token ไว้ใน localStorage ของเบราว์เซอร์ พอผู้ใช้ปิดแท็บ
แล้วเปิดใหม่ หน้าเว็บรู้แค่ว่า "มี token อยู่" แต่ไม่รู้ว่า:

- token ยังไม่หมดอายุใช่ไหม
- เจ้าของ token คนนี้คือใคร ชื่ออะไร บทบาทอะไร

ยิง `/me` หนึ่งครั้งได้คำตอบทั้งสองอย่าง — ผ่าน = ใช้ได้และนี่คือข้อมูลเขา ·
ได้ 401 = token ใช้ไม่ได้แล้ว ให้เด้งไปหน้าล็อกอิน

## 6. `app/main.py` — แทนของเฟส 0

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.users import auth_router as auth
from app.users.service import ensure_admin


@asynccontextmanager
async def lifespan(_app):
    """ตอนเซิร์ฟเวอร์เริ่ม: สร้างบัญชี admin จาก env ถ้ายังไม่มี"""
    ensure_admin()
    yield


app = FastAPI(title="ระบบจัดการอู่ซ่อมรถ", lifespan=lifespan)
app.include_router(auth.router)


@app.get("/api/health")
def health():
    """GET /api/health: เช็คว่าเซิร์ฟเวอร์ยังทำงาน"""
    return {"ok": True}
```

**อ่านโค้ดนี้ยังไง**

```python
@asynccontextmanager
async def lifespan(_app):
    ensure_admin()      # ← โค้ดตรงนี้รันตอนแอป "เริ่ม"
    yield               # ← แอปทำงานปกติอยู่ตรงนี้ (นาน ๆ)
                        # ← โค้ดหลัง yield จะรันตอนแอป "ปิด" (เฟสนี้ยังไม่มี)
```

`lifespan` คือที่สำหรับโค้ดที่ต้องรันครั้งเดียวตอนแอปเริ่มและตอนปิด
เราใช้มันเรียก `ensure_admin()` เพื่อสร้าง admin คนแรก

> ถ้าไปเจอ `@app.on_event("startup")` ในบทความเก่า ๆ — อันนั้นเลิกใช้แล้ว
> `lifespan` คือตัวที่มาแทน

`app.include_router(auth.router)` — บรรทัดนี้แหละที่ทำให้ `/api/auth/login`
เรียกได้จริง ไม่ใส่ = เขียน router ไว้แต่ไม่มีใครรู้จัก

## 7. `tests/conftest.py` — โครงเทสต์ที่ใช้ยาวทั้งโปรเจ็ค

**ขั้นนี้ทำอะไร** เตรียม "ของใช้ร่วม" ให้ไฟล์เทสต์ทุกไฟล์ในโปรเจกต์
ลงแรงเขียนครั้งเดียวที่นี่ แล้วเทสต์ทุกเฟสหลังจากนี้หยิบไปใช้ได้เลย

**`conftest.py` คือชื่อพิเศษที่ pytest รู้จัก** — ของที่ประกาศไว้ในนี้
ไฟล์เทสต์ข้าง ๆ เรียกใช้ได้เลยโดยไม่ต้อง import

**สร้างไฟล์ใหม่** `backend/tests/conftest.py`

```python
import os

os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import models
from app.auth import create_token, hash_password
from app.db import Base, SessionLocal, engine
from app.main import app


@pytest.fixture(scope="session")
def migrated():
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def clean(migrated):
    with engine.begin() as conn:
        conn.execute(text(f"truncate {', '.join(Base.metadata.tables)} restart identity cascade"))


@pytest.fixture
def client():
    return TestClient(app)


PW_HASH = hash_password("pw")
ROLES = ("admin", "employee", "mechanic")


@pytest.fixture
def users():
    with SessionLocal() as s:
        out = {r: models.User(username=r, full_name=r, role=r, password_hash=PW_HASH) for r in ROLES}
        s.add_all(out.values())
        s.commit()
    return out


@pytest.fixture
def h(users):
    return {r: {"Authorization": f"Bearer {create_token(u.id)}"} for r, u in users.items()}
```

### สามบรรทัดแรกคือบรรทัดที่อันตรายที่สุดในโปรเจกต์

```python
import os
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]   # ← ต้องอยู่ตรงนี้เท่านั้น
import pytest
```

**บรรทัดนี้ต้องอยู่ก่อน `import app.db` เสมอ** เพราะ `db.py` อ่าน `DATABASE_URL`
ตอนถูก import ครั้งแรก (ข้อ 1) ถ้าปล่อยให้ import เกิดก่อน มันจะจำ URL
ของฐานข้อมูลจริงไว้ แล้ว...

```
fixture clean  →  truncate ทุกตาราง  →  บนฐานข้อมูลจริง 💀
```

**เทสต์จะล้างข้อมูลจริงทิ้งทั้งหมด** ทุกครั้งที่รัน นี่คือเหตุผลที่ยอมผิดกฎ
"import ต้องอยู่บนสุด"

> ตัวตรวจสไตล์ทั่วไปจะเตือนกฎนี้ (E402) แต่ ruff ยกเว้นให้เองเมื่อบรรทัดก่อนหน้าเป็นการตั้ง
> `os.environ` เพราะรู้ว่าเป็นท่ามาตรฐาน **ไม่ต้องใส่ `# noqa: E402`** ใส่ไปแล้ว `ruff check` จะเตือนกลับว่า noqa นี้ไม่ได้ใช้
>
> อีกเรื่อง: `ruff check --fix` จะเรียง import ใหม่ แต่ไม่ย้ายข้ามบรรทัด `os.environ[...] = ...`
> เพราะมันเรียงเฉพาะกลุ่ม import ที่ติดกัน บรรทัดอันตรายนี้จึงอยู่ที่เดิมเสมอ

### fixture แต่ละตัวทำอะไร

| fixture | ทำอะไร | รันเมื่อไหร่ |
|---|---|---|
| `migrated` | สร้างตารางด้วย alembic | **ครั้งเดียว**ต่อการรันทั้งชุด (`scope="session"`) |
| `clean` | ล้างข้อมูลทุกตาราง | **ก่อนทุกเทสต์** อัตโนมัติ (`autouse=True`) |
| `client` | ตัวยิง request เข้า API | เมื่อเทสต์ขอ |
| `users` | สร้างผู้ใช้ครบ 3 บทบาท | เมื่อเทสต์ขอ |
| `h` | header ที่ล็อกอินแล้วของ 3 บทบาท | เมื่อเทสต์ขอ |

**`autouse=True` บน `clean`** แปลว่าไม่ต้องเขียนชื่อมันในเทสต์เลย มันรันให้เอง
— ข้อดีคือ**ลืมไม่ได้** ถ้าต้องเขียนเองทุกครั้งจะมีสักเทสต์ที่ลืม แล้วข้อมูลค้าง
จากเทสต์ก่อนหน้าจะทำให้เทสต์ถัดไปพังแบบหาสาเหตุไม่เจอ

**ทำไมใช้ `truncate` ไม่ใช่ลบตารางแล้วสร้างใหม่**

```sql
truncate ทุกตาราง restart identity cascade
--                ^รีเซ็ต id     ^ไม่ต้องเรียงลำดับตาม FK
```

`truncate` เร็วกว่า drop/create มาก เลยรันก่อนทุกเทสต์ไหว ส่วน migration
(ที่ช้า) รันครั้งเดียวต่อการรันทั้งชุดพอ

- `restart identity` — รีเซ็ต id กลับไปเริ่มที่ 1 ทุกเทสต์ ไม่งั้น id
  จะวิ่งขึ้นเรื่อย ๆ และเทสต์ที่เผลอเขียน `id == 1` ไว้จะพังแบบสุ่ม
- `cascade` — ลบข้ามตารางที่อ้างถึงกันได้โดยไม่ต้องจัดลำดับเอง

**`PW_HASH = hash_password("pw")` คำนวณครั้งเดียวไว้นอกฟังก์ชัน**

จำเรื่อง Argon2 ช้าโดยตั้งใจได้ไหม (~0.05 วินาที) ถ้า hash ใหม่ทุกครั้งที่
สร้างผู้ใช้ในเทสต์ — 3 คน × 100 เทสต์ = 15 วินาทีที่เสียไปเปล่า ๆ

**`h` ใช้ยังไง** — ยิง request ในฐานะบทบาทไหนก็หยิบอันนั้น

```python
client.get("/api/auth/me", headers=h["mechanic"])   # ยิงในฐานะช่าง
client.get("/api/users", headers=h["admin"])        # ยิงในฐานะ admin
```

## 8. `tests/test_auth.py`

**ขั้นนี้ทำอะไร** เขียนเทสต์ให้ระบบล็อกอิน แบ่งเป็นสองส่วนที่เขียนคนละจังหวะกัน

| ส่วน | ทดสอบอะไร | เขียนได้เมื่อ |
|---|---|---|
| ส่วนแรก | เรียกฟังก์ชันใน `auth.py` ตรง ๆ | เขียน `auth.py` + `conftest.py` เสร็จ (ยังไม่ต้องมี router) |
| ส่วนที่สอง | ยิง API จริงผ่าน HTTP | เขียน `users/` + `main.py` เสร็จแล้ว |

ถ้าทำตามลำดับในไกด์มาตลอด ตอนนี้เขียนได้ทั้งสองส่วนเลย — แต่ที่แยกให้ดูเพราะ
อยากให้เห็นว่า**เทสต์ที่ดีไม่ต้องรอให้ระบบเสร็จทั้งหมดก่อน** ส่วนไหนเขียนเสร็จ
ทดสอบส่วนนั้นได้ทันที

### ส่วนแรก — `auth.py` ตรง ๆ

```python
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app import models
from app.auth import JWT_SECRET, create_token, current_user, hash_password, verify_password
from app.db import SessionLocal


def bearer(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def rejected(token_or_none):
    """current_user must answer 401 with the Thai message, never 500 or a user."""
    with SessionLocal() as db, pytest.raises(HTTPException) as e:
        current_user(token_or_none, db)
    assert (e.value.status_code, e.value.detail) == (401, "กรุณาเข้าสู่ระบบ")


# --- password ---

def test_hash_is_not_the_password_and_verifies():
    stored = hash_password("secret1")
    assert stored != "secret1" and stored.startswith("$argon2id$")
    assert verify_password("secret1", stored)
    assert not verify_password("wrong", stored)


def test_same_password_hashes_differently():
    assert hash_password("secret1") != hash_password("secret1")   # salt สุ่มต่อครั้ง


# --- token ---

def test_token_carries_user_id_and_expiry():
    payload = jwt.decode(create_token(7), JWT_SECRET, algorithms=["HS256"])
    assert payload["user_id"] == 7
    assert payload["exp"] > datetime.now(timezone.utc).timestamp()


# --- current_user ---

def test_valid_token_returns_user(users):
    with SessionLocal() as db:
        assert current_user(bearer(create_token(users["mechanic"].id)), db).username == "mechanic"


def test_no_header():
    rejected(None)


def test_garbage_token():
    rejected(bearer("junk"))


def test_token_signed_with_another_secret(users):
    rejected(bearer(jwt.encode({"user_id": users["admin"].id}, "not-our-secret", algorithm="HS256")))


def test_expired_token(users):
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    rejected(bearer(jwt.encode({"user_id": users["admin"].id, "exp": past}, JWT_SECRET, algorithm="HS256")))


def test_token_without_user_id():
    rejected(bearer(jwt.encode({"sub": "1"}, JWT_SECRET, algorithm="HS256")))


def test_user_no_longer_exists():
    rejected(bearer(create_token(999)))


def test_deactivated_user_rejected_even_with_valid_token(users):
    token = create_token(users["employee"].id)
    with SessionLocal() as s:
        s.get(models.User, users["employee"].id).is_active = False
        s.commit()
    rejected(bearer(token))
```

### อ่านเทสต์ชุดนี้ยังไง

**ตัวช่วยสองตัวบนสุดของไฟล์**

```python
def bearer(token):      # สร้าง object แบบที่ HTTPBearer จะสร้างให้ตอนมี header จริง
def rejected(t):        # ยืนยันว่าถูกปฏิเสธด้วย 401 + ข้อความไทย
```

`bearer()` ทำให้เราเรียก `current_user()` ตรง ๆ ได้โดยไม่ต้องยิง request จริง
เร็วกว่าและเจาะจงกว่า

`rejected()` ตรวจ**ทั้งรหัสและข้อความ** — สำคัญเพราะกรณีปฏิเสธมีหลายแบบ
แต่ทุกแบบต้องได้ผลเหมือนกันเป๊ะ: **401 "กรุณาเข้าสู่ระบบ"**
ไม่ใช่ 500 (แปลว่าโค้ดพัง) และไม่ใช่ได้ผู้ใช้กลับมา (แปลว่าหลุด)

**เทสต์แต่ละตัวจับอะไร**

| เทสต์ | ยืนยันว่า |
|---|---|
| `hash_is_not_the_password` | รหัสไม่ได้เก็บตรง ๆ และตรวจกลับได้ |
| `same_password_hashes_differently` | salt สุ่มจริง — รหัสเดียวกันได้ hash คนละอัน |
| `token_carries_user_id_and_expiry` | token มี `user_id` กับวันหมดอายุครบ |
| `token_signed_with_another_secret` | **ปลอม token เองไม่ได้** เซ็นด้วยกุญแจอื่นถูกปฏิเสธ |
| `expired_token` | token ที่ `exp` ผ่านไปแล้ว 1 นาที ใช้ไม่ได้ |
| `token_without_user_id` | token ที่ไม่มีช่องที่เราต้องการ ถูกปฏิเสธ ไม่ใช่ 500 |
| `user_no_longer_exists` | token ชี้ไปที่ผู้ใช้ที่ไม่มีแล้ว ถูกปฏิเสธ |
| `deactivated_user_rejected` | **บัญชีที่ถูกปิด ใช้ token เดิมต่อไม่ได้** |

**ตัวสุดท้ายสำคัญที่สุด** — มันคือเหตุผลทั้งหมดที่เรายอมเสีย query หนึ่งครั้ง
ต่อ request เพื่อโหลดผู้ใช้จากฐานใหม่ทุกครั้ง (จำเรื่อง payload มีแค่ `user_id` ได้ไหม)
ถ้าเชื่อแต่ token อย่างเดียว คนที่เพิ่งโดนปิดบัญชีจะยังใช้ระบบต่อได้อีก 12 ชั่วโมง

> เฟสนี้ยังไม่มี API ปิดบัญชี เทสต์เลยแก้ฐานตรง ๆ ไปก่อน — เฟส 2 มีแล้ว
> จะมีเทสต์แบบยิง API จริงอีกที

> **เทสต์ชุดนี้จับสองบั๊กที่เตือนไว้ข้างบนได้จริง**
> - ตั้งชื่อพารามิเตอร์ `verify_password` ชนกับ `password_hash` → เทสต์รหัสผ่านแดง
> - สะกด `algorithm=` ขาด s → `test_valid_token_returns_user` ได้ 401
> ถ้าเทสต์สองตัวนี้แดง ให้กลับไปดูข้อ 3 ก่อนเลย

### รันเทสต์ส่วนแรก

```
docker compose run --rm api pytest
```

ต้อง **passed ทั้งหมด ไม่มี failed** (ตอนนี้จะมีราว ๆ 12 ตัว รวม `test_health` จากเฟส 0)

### ส่วนที่สอง — ยิง API (ต่อท้ายไฟล์เดิม หลังเขียน `users/` และ `main.py`)

เติม import สองบรรทัด — `select` ไว้กลุ่มเดียวกับ `fastapi` / `jwt` · `ensure_admin` ไว้กลุ่ม `from app...`

```python
from sqlalchemy import select

from app.users.service import ensure_admin
```

เติมท้ายไฟล์

```python
# --- API ---

def test_login_and_me(client, users):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "pw"})
    assert r.status_code == 200
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    assert me["role"] == "admin" and "password_hash" not in me


def test_wrong_password(client, users):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401 and r.json()["detail"] == "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"


def test_unknown_user_same_message_as_wrong_password(client, users):
    a = client.post("/api/auth/login", json={"username": "nobody", "password": "pw"})
    b = client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert a.json()["detail"] == b.json()["detail"]


def test_me_needs_token(client, h):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=h["mechanic"]).json()["username"] == "mechanic"


def test_ensure_admin_only_when_no_users(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "owner")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret99")
    ensure_admin()
    ensure_admin()
    with SessionLocal() as s:
        assert [u.username for u in s.scalars(select(models.User))] == ["owner"]
```

### อ่านเทสต์ส่วนนี้ยังไง

**`test_login_and_me` — เดินทางจริงทั้งเส้น**

```
POST /api/auth/login  →  ได้ token  →  แนบ token ยิง GET /api/auth/me  →  ได้ข้อมูลตัวเอง
```

และเช็คด้วยว่า `password_hash` **ไม่หลุด**ออกมาใน response (ผลของการที่
`UserOut` ไม่ประกาศช่องนี้ไว้)

**`test_unknown_user_same_message_as_wrong_password`** — ยิงสองแบบแล้วเทียบว่า
ข้อความที่ได้ตรงกันเป๊ะ นี่คือเทสต์ที่กันไม่ให้ใครเผลอ "ปรับปรุง" ข้อความ
ให้ละเอียดขึ้นในอนาคต แล้วเปิดช่องให้คนนอกไล่เดาว่าบัญชีไหนมีจริง

**`test_me_needs_token`** — เช็คแค่ว่า `current_user` ถูกต่อเข้ากับ route จริง
ไม่ได้ทดสอบกรณีปฏิเสธแบบละเอียดซ้ำ เพราะส่วนแรกทำครบไปแล้ว
**เทสต์ที่ดีไม่ทดสอบเรื่องเดียวกันซ้ำสองชั้น**

**`test_ensure_admin_only_when_no_users` — เรียกสองรอบ ต้องได้คนเดียว**

พิสูจน์ว่าเรียกซ้ำกี่ครั้งก็ไม่สร้างซ้ำ (ซึ่งเกิดขึ้นจริงทุกครั้งที่รีสตาร์ทแอป)

`monkeypatch.setenv` เปลี่ยน env เฉพาะในเทสต์นี้ จบแล้วคืนค่าเดิมให้เอง

> ตรงนี้ใช้ได้เพราะ `ensure_admin` อ่าน `ADMIN_*` **ตอนถูกเรียก**
> ต่างจาก `JWT_SECRET` ใน `auth.py` ที่อ่านตอน import — อันนั้น `monkeypatch` ไม่มีผล
> (เตือนไว้แล้วในข้อ 3)

### รันเทสต์ทั้งหมด

```
docker compose run --rm api pytest
```

ต้อง **passed ทั้งหมด ไม่มี failed** (ราว ๆ 17 ตัว)

backend เสร็จแล้ว ต่อไปเป็นฝั่งหน้าจอ

---

# ส่วนหน้าจอ

**ส่วนนี้จะได้อะไร** หน้าล็อกอินที่ใช้ได้จริง + โครงหน้าจอ (แถบเมนู) ที่ทุกหน้า
ในเฟสหลังจะอยู่ข้างใน

ลำดับ: `index.css` (สี) → `api.js` (คุยกับ backend) → `auth.jsx` (จำว่าใครล็อกอิน)
→ `Icon` → `LoginPage` → `AppLayout` → `main.jsx` (ผูก URL)

## 9. axios · TanStack Query · react-hook-form

**ไม่ต้องลงอะไรเพิ่ม** — ทั้งสามตัวอยู่ใน `package.json` ตั้งแต่เฟส 0 เฟสนี้เริ่มใช้ครั้งแรก

| ตัว | หน้าที่ในระบบนี้ | เจอครั้งแรกที่ |
|---|---|---|
| axios | ยิง HTTP request | ข้อ 11 `api.js` |
| TanStack Query | **`useQuery`** ดึงข้อมูลมาแสดง + จำไว้ · **`useMutation`** สั่งบันทึก/ล็อกอิน พร้อมสถานะ "กำลังส่ง" และ error | ข้อ 11 (ตั้งค่า) · ข้อ 14 (`useMutation`) · เฟส 2 (`useQuery`) |
| react-hook-form | **`useForm`** เก็บค่าที่พิมพ์ในฟอร์ม | ข้อ 14 `LoginPage` |

> **ถ้า `npm run build` ฟ้องว่าหาแพ็กเกจไหนไม่เจอ**
> แปลว่า container ยังใช้ `node_modules` ชุดเก่า
> ```
> docker compose run --rm web npm install
> docker compose restart web
> ```
> ต้องสั่งผ่าน container เพราะ `node_modules` อยู่ใน volume ของมัน ไม่ได้อยู่บนเครื่องเรา

## 10. `src/index.css` — สีและคลาสกลาง (แทนของเฟส 0)

**ขั้นนี้ทำอะไร** กำหนดสีและคลาสที่ใช้ร่วมกันทั้งระบบไว้ที่เดียว

**เปิด** `frontend/src/index.css` → แทนทั้งไฟล์

```css
@import "tailwindcss";

@theme {
  --font-sans: "IBM Plex Sans Thai", ui-sans-serif, system-ui, sans-serif;
  --color-ink: #111827;
  --color-muted: #6b7280;
  --color-line: #e5e7eb;
  --color-surface: #f9fafb;
  --color-accent: #2563eb;
  --color-accent-soft: #eff6ff;
  --color-accent-ink: #1d4ed8;
  --color-warn-soft: #fffbeb;
  --color-warn-ink: #b45309;
  --color-ok-soft: #f0fdf4;
  --color-ok-ink: #15803d;
  --color-danger: #dc2626;
  --color-danger-soft: #fef2f2;
  --color-neutral-soft: #f3f4f6;
}

@layer base {
  body { @apply bg-white text-ink antialiased; }
  :focus-visible { @apply outline-2 outline-offset-2 outline-accent; }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { transition: none !important; animation: none !important; }
  }
}

@layer components {
  .page-title { @apply text-xl font-semibold lg:text-2xl; }
  .card { @apply rounded-xl border border-line bg-white p-4; }
  .label { @apply mb-1 block text-sm text-muted; }
  .field-error { @apply text-sm font-medium text-danger; }
  .input { @apply min-h-11 w-full rounded-lg border border-line bg-white px-3 py-2 text-base transition-colors duration-150 focus:border-accent focus:ring-3 focus:ring-accent-soft focus:outline-none disabled:bg-surface disabled:text-muted; }

  .btn { @apply inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-lg px-4 font-semibold whitespace-nowrap transition duration-150 disabled:cursor-not-allowed disabled:opacity-50; }
  .btn-primary { @apply bg-accent text-white hover:bg-accent-ink; }
  .btn-ghost { @apply text-ink hover:bg-surface; }
  .btn-icon { @apply min-w-11 px-0; }
}
```

### อ่านไฟล์นี้ยังไง — แบ่งเป็นสามบล็อก

| บล็อก | ใส่อะไร |
|---|---|
| `@theme` | **ตัวแปรสี** ประกาศแล้วได้คลาส `bg-accent` `text-muted` ใช้ทันที |
| `@layer base` | กฎที่ใช้กับ tag พื้นฐานทั้งหน้า |
| `@layer components` | **คลาสของเราเอง** (`.btn` `.input` `.card`) |

**`@theme` คือวิธีตั้งค่าของ Tailwind v4** — เวอร์ชันนี้ไม่มี `tailwind.config.js` แล้ว
ประกาศตัวแปรตรงนี้ในไฟล์ CSS เลย

**ทำไมห้ามเขียนสีเป็น hex ในคอมโพเนนต์** — วันที่อยากเปลี่ยนสีเน้นของระบบ
ถ้า `#2563eb` กระจายอยู่ใน 40 ไฟล์คือไล่แก้ทั้งวันและตกหล่นแน่นอน
อยู่ที่นี่ที่เดียว แก้บรรทัดเดียวเปลี่ยนทั้งระบบ

**สีสถานะประกาศครบชุดตั้งแต่ตอนนี้** ทั้งที่เฟสนี้ยังไม่ได้ใช้เลยสักสี
เพราะมันคือ**ชุดสีของระบบ** ไม่ใช่ฟีเจอร์ของเฟสไหน (เฟส 2 ป้ายสถานะจะเริ่มใช้)

**`min-h-11` = 44px โผล่ในทุกอย่างที่กดได้**

44px คือขนาดต่ำสุดที่นิ้วกดไม่พลาด เป็นตัวเลขมาตรฐานที่ Apple กับ Google แนะนำตรงกัน
อู่ใช้มือถือเป็นหลัก ปุ่มเล็กกว่านี้คือกดพลาดทั้งวัน

**`:focus-visible` ต้องเห็นชัด** — คนที่ใช้ปุ่ม Tab เดินหน้าจอ (แทนเมาส์)
ต้องรู้ตลอดว่าตอนนี้อยู่ตรงไหน ถ้าลบเส้นนี้ทิ้งเพราะ "ไม่สวย" คนกลุ่มนั้นใช้ระบบไม่ได้เลย

**`prefers-reduced-motion`** — ปิดแอนิเมชันทั้งหมดให้คนที่ตั้งค่าเครื่องไว้ว่า
ไม่อยากเห็นการเคลื่อนไหว (บางคนเวียนหัวจริง ๆ)

> **`.btn` คือรูปทรง · `.btn-primary` คือสี — ต้องใส่คู่กันเสมอ**
> ```jsx
> <button className="btn btn-primary">   // ✅
> <button className="btn-primary">       // ❌ ไม่มีรูปทรง
> ```
> และ **ห้ามเขียน `@apply btn` ข้างใน `.btn-primary`** เพื่อรวบให้เหลือคลาสเดียว
> เพราะ Tailwind v4 ไม่ยอมให้ `@apply` คลาสที่เราประกาศเอง
> build จะพังด้วย `Cannot apply unknown utility class btn`

**`btn-ghost btn-icon`** ปุ่มไอคอนล้วนที่ไม่มีพื้นหลัง · `min-w-11` บังคับกว้าง
อย่างน้อย 44px แม้ข้างในมีแค่ไอคอนเล็ก ๆ (เฟส 2 ปุ่มปิดป๊อปอัพใช้คู่นี้)

คลาสอื่น (`modal` `table` `badge` `tabs`) ยังไม่ใส่ — เฟส 2 ที่มีของใช้ค่อยเติม

## 11. `src/api.js` — ที่เดียวที่คุยกับ backend

**ขั้นนี้ทำอะไร** ทุกการคุยกับ backend ในระบบนี้ต้องผ่านไฟล์นี้ไฟล์เดียว
ไม่มีหน้าไหนเรียก axios เอง

**ทำไมต้องรวมไว้ที่เดียว** — ถ้าแต่ละหน้าเรียก axios เอง ทุกหน้าต้องจำ:

- แนบ token ทุกครั้ง
- เจอ 401 ต้องเด้งไปล็อกอิน
- แปล error เป็นภาษาไทย

**ลืมข้อใดข้อหนึ่งในหน้าใดหน้าหนึ่ง = บั๊ก** รวมไว้ที่นี่แล้วลืมไม่ได้

**สร้างไฟล์ใหม่** `frontend/src/api.js`

```js
import { QueryClient } from "@tanstack/react-query";
import axios from "axios";

// token ใน localStorage: อ่าน / เก็บ / ลบ
export const getToken = () => localStorage.getItem("token");
export const setToken = (token) => localStorage.setItem("token", token);
export const removeToken = () => localStorage.removeItem("token");

// แปลง error validation 1 รายการจาก FastAPI (422) → ข้อความไทย
const validationMessage = ({ type, ctx = {} }) =>
  ({
    missing: "กรอกข้อมูลไม่ครบ",
    greater_than: `ต้องมากกว่า ${ctx.gt}`,
    greater_than_equal: `ต้องไม่น้อยกว่า ${ctx.ge}`,
    less_than: `ต้องน้อยกว่า ${ctx.lt}`,
    less_than_equal: `ต้องไม่เกิน ${ctx.le}`,
    string_too_short: "ข้อความสั้นเกินไป",
    string_too_long: "ข้อความยาวเกินไป",
  })[type] ?? "รูปแบบข้อมูลไม่ถูกต้อง";

// แปลง body error จาก backend → ข้อความเดียวไว้โชว์ผู้ใช้
function toErrorMessage(data) {
  const d = data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return "ข้อมูลไม่ถูกต้อง: " + [...new Set(d.map(validationMessage))].join(", ");
  return "เกิดข้อผิดพลาด กรุณาลองใหม่";
}

// เรียก backend /api{path} แนบ token → คืน data (204 = null), 401 ลบ token แล้วไปหน้า login
export async function api(path, { method = "GET", body } = {}) {
  const token = getToken();

  try {
    const response = await axios.request({
      url: `/api${path}`,
      method,
      data: body,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    return response.status === 204 ? null : response.data;
  } catch (error) {
    if (error.response?.status === 401 && path !== "/auth/login") {
      removeToken();
      location.assign("/login");
    }
    throw new Error(toErrorMessage(error.response?.data));
  }
}

// cache ข้อมูลจาก backend ของทั้งแอป
// queryKey คือ path ของ API แยกเป็นท่อน: ["products", id, "lots"] → GET /products/{id}/lots
// ท่อนแรกเป็นกลุ่มข้อมูล สั่ง invalidateQueries({ queryKey: ["products"] }) ทีเดียว โหลดใหม่ทุกอย่างของสินค้า
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: ({ queryKey }) => api("/" + queryKey.join("/")),
      retry: false, // error จาก backend (404, 403) ลองซ้ำก็ได้ผลเดิม
    },
  },
});
```

### อ่านโค้ดนี้ยังไง

ไฟล์นี้ให้ของ 3 อย่าง:

```
getToken / setToken / removeToken   จัดการ token ใน localStorage
api(path, options)                  ยิง request หนึ่งครั้ง
queryClient                         ที่เก็บ (cache) ข้อมูลทั้งแอป ของ TanStack Query
```

**`toErrorMessage` แยกสองกรณี** — backend ส่ง error กลับมาได้ 2 แบบ

1. **`detail` เป็นข้อความ** — เราเขียนเองด้วย `HTTPException` เป็นไทยอยู่แล้ว **แสดงตรง ๆ**
   ```json
   {"detail": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}
   ```
2. **`detail` เป็น list** — ข้อมูลไม่ตรง schema pydantic ตีกลับก่อนถึงโค้ดเรา ข้อความเป็นอังกฤษ
   ```json
   {"detail": [{"type": "missing", "loc": ["body", "password"], "msg": "Field required"}]}
   ```
   **แปลจาก `type` ไม่ใช่ `msg`** เพราะ `type` เป็นรหัสตายตัว ส่วน `msg`
   pydantic เปลี่ยนคำเมื่อไหร่ก็ได้ตอนอัปเดตเวอร์ชัน

   `new Set` กันข้อความซ้ำ — เว้นว่าง 5 ช่องจะได้ "กรอกข้อมูลไม่ครบ" ครั้งเดียว
   ไม่ใช่ห้าครั้ง

**เจอ 401 แล้วเด้งไปหน้าล็อกอินให้เอง**

token หมดอายุใน 12 ชั่วโมง ถ้าไม่ดักตรงนี้ ผู้ใช้ที่เปิดหน้าทิ้งไว้ข้ามวัน
จะเจอหน้าจอที่กดอะไรก็ไม่มีอะไรเกิดขึ้น โดยไม่รู้ว่าเพราะอะไร

```js
if (error.response?.status === 401 && path !== "/auth/login") {
//                                    ^ ยกเว้นหน้าล็อกอินเอง
```

**ข้อยกเว้นนั้นสำคัญ** — ไม่ใส่ พอกรอกรหัสผิดที่หน้าล็อกอิน (ซึ่งตอบ 401)
หน้าจะรีเฟรชตัวเองทิ้ง ข้อความ "รหัสผ่านไม่ถูกต้อง" ยังไม่ทันโผล่ให้เห็นเลย

**`?.` ที่เห็นเต็มไปหมดคืออะไร** — axios โยน error เองเมื่อสถานะไม่ใช่ 2xx
และข้อมูลจะอยู่ใน `error.response.data`

แต่ถ้า**เน็ตหลุดหรือ API ดับ** จะไม่มี response เลย → `error.response` เป็น
`undefined` → เขียน `.data` ต่อจะพัง `?.` คือ "ถ้าตัวหน้าไม่มี ก็หยุดแล้วคืน
`undefined`" แล้วเราได้ข้อความกลาง ๆ "เกิดข้อผิดพลาด กรุณาลองใหม่" แทนจอขาว

**เกร็ดสองข้อ**

- `data: body` — axios แปลง object เป็น JSON และตั้ง `Content-Type` ให้เอง
  ไม่ต้อง `JSON.stringify` เอง
- `status === 204 ? null : ...` — 204 แปลว่าสำเร็จแต่ไม่มีข้อมูลส่งกลับ
  คืน `null` ให้ทุกหน้าเช็คแบบเดียวกันได้

> **ทำไมเก็บ token ใน `localStorage` ทั้งที่หลายคนบอกว่าไม่ปลอดภัย**
> ระบบนี้เป็นอู่เดียว ใช้เครื่องในร้าน API กับเว็บอยู่โดเมนเดียวกัน
> `localStorage` ง่ายกว่า cookie มากและไม่ต้องจัดการ CSRF
> วันหน้าถ้าเปิดให้เข้าจากภายนอกค่อยย้ายไป httpOnly cookie

### `queryClient` — ที่เก็บข้อมูลจาก backend ของทั้งแอป

TanStack Query ทำงานแบบนี้: หน้าไหนอยากได้ข้อมูล ก็ขอด้วย **กุญแจ (`queryKey`)**

```jsx
const { data, error } = useQuery({ queryKey: ["users"] });   // เฟส 2
```

- ครั้งแรก: ยังไม่มีในที่เก็บ → เรียก `queryFn` ไปดึงมา → เก็บไว้ใต้กุญแจ `["users"]`
- หน้าอื่นขอกุญแจเดียวกัน → **ได้ของชุดเดียวกัน ไม่ยิงซ้ำ**
- บันทึกอะไรแล้วสั่ง `invalidateQueries({ queryKey: ["users"] })` → ทุกหน้าที่ใช้กุญแจนี้โหลดใหม่เอง

**`queryFn` ตัวกลางตัวเดียว: กุญแจ = path ของ API**

```js
queryFn: ({ queryKey }) => api("/" + queryKey.join("/")),
```

```
["users"]                    → GET /users
["products", "5"]            → GET /products/5
["products", "5", "lots"]    → GET /products/5/lots
```

ตั้งไว้ที่นี่ครั้งเดียว ทุกหน้าเขียนแค่ `useQuery({ queryKey: [...] })` ไม่ต้องเขียนว่าดึงยังไงซ้ำทุกที่
และกุญแจอ่านแล้วรู้ทันทีว่ายิง URL ไหน

**ทำไมแยกเป็นท่อน `["products", "5", "lots"]` ไม่เขียน `["/products/5/lots"]` ก้อนเดียว** —
`invalidateQueries({ queryKey: ["products"] })` จับ **ทุกกุญแจที่ขึ้นต้นด้วย `"products"`**
สั่งทีเดียวได้ทั้งรายการสินค้า · สินค้าตัวนั้น · Lot · สมุดสต็อก (เฟส 3 ใช้ท่านี้)

**`retry: false`** — ค่าเริ่มต้นของ TanStack Query คือพังแล้วลองซ้ำ 3 รอบ เหมาะกับเน็ตหลุดชั่วคราว
แต่ error ที่เราเจอจริงคือ 404 / 403 จาก backend ลองกี่รอบก็ได้ผลเดิม และทำให้ข้อความ error ขึ้นช้าไปหลายวินาที

**ของที่ TanStack Query ทำให้ ที่เดิมต้องเขียนเอง**

| เรื่อง | เขียนเอง | TanStack Query |
|---|---|---|
| สถานะกำลังโหลด / error | `useState` สองตัวทุกหน้า | ได้ `data` `error` `isPending` มาเลย |
| บันทึกแล้วโหลดใหม่ | จำเองว่าต้อง `reload()` อะไรบ้าง | `invalidateQueries` ตามกลุ่ม |
| หน้าสองหน้าใช้ข้อมูลเดียวกัน | ยิงซ้ำ | ใช้ของชุดเดียวกัน |
| กดกลับมาหน้าเดิม | ขึ้น "กำลังโหลด…" ใหม่ | ข้อมูลเดิมขึ้นทันที แล้วอัปเดตเบื้องหลัง |
| สลับแท็บเบราว์เซอร์แล้วกลับมา | ข้อมูลค้างเป็นของเก่า | ดึงใหม่เอง |

> `error` ที่ `useQuery` / `useMutation` ให้มาเป็น **object** `Error` ไม่ใช่ข้อความ
> แสดงผลต้องเขียน `error.message` (ข้อความไทยที่ `toErrorMessage` แปลไว้แล้ว)

ตัวจัดรูปแบบเงินกับวันที่ยังไม่ใส่ — เฟส 3 ที่เริ่มมีตัวเลขเงินค่อยเติมท้ายไฟล์นี้

## 12. `src/auth.jsx`

**ขั้นนี้ทำอะไร** จำไว้ว่า "ตอนนี้ใครล็อกอินอยู่" แล้วแจกข้อมูลนั้นให้ทุกหน้า
ที่ต้องใช้ โดยไม่ต้องส่ง prop ไล่ลงไปทีละชั้น

**Context คืออะไร** — วิธีของ React ในการวางข้อมูลไว้ตรงกลาง แล้วให้คอมโพเนนต์
ไหนก็ได้ที่อยู่ข้างในหยิบใช้ได้เลย

```
<AuthProvider>              ← เก็บ user ไว้ตรงนี้
   └── <AppLayout>
        └── <UsersPage>
             └── <UserFormPage>  ← เรียก useAuth() หยิบ user ได้เลย ไม่ต้องส่งผ่าน 3 ชั้น
```

**สร้างไฟล์ใหม่** `frontend/src/auth.jsx` (นามสกุล `.jsx` ไม่ใช่ `.js` เพราะมี JSX ข้างใน)

```jsx
import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, queryClient, setToken, removeToken } from "./api";

const AuthContext = createContext(null);

export const ROLE_NAME = { admin: "เจ้าของอู่", employee: "พนักงาน", mechanic: "ช่าง" };

// Context ผู้ใช้: เปิดแอปถ้ามี token ดึง /auth/me, user = undefined(กำลังโหลด) | null | object
export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    if (!getToken()) {
      setUser(null);
      return;
    }
    api("/auth/me")
      .then((user) => setUser(user))
      .catch(() => setUser(null));
  }, []);

  // POST /auth/login → เก็บ token + ตั้ง user
  const login = async (username, password) => {
    const response = await api("/auth/login", { method: "POST", body: { username, password } });
    setToken(response.access_token);
    setUser(response.user);
  };

  // ลบ token + ล้าง cache (กันคนถัดไปเห็นข้อมูลค้าง เช่นต้นทุนที่เห็นได้เฉพาะ admin) + ล้าง user
  const logout = () => {
    removeToken();
    queryClient.clear();
    setUser(null);
  };
  return <AuthContext.Provider value={{ user, login, logout }}> {children} </AuthContext.Provider>;
}

// ดึง { user, login, logout } จาก AuthContext
export const useAuth = () => useContext(AuthContext);
```

### อ่านโค้ดนี้ยังไง

**`user` มีสามสถานะ ไม่ใช่สอง — จุดที่มือใหม่พลาดกันเยอะ**

| ค่า | แปลว่า | หน้าจอต้องทำ |
|---|---|---|
| `undefined` | **ยังไม่รู้** กำลังถาม `/me` อยู่ | ยังไม่ต้องวาดอะไร |
| `null` | รู้แล้วว่า**ไม่ได้ล็อกอิน** | เด้งไปหน้าล็อกอิน |
| object | รู้แล้วว่า**ล็อกอินอยู่** เป็นคนนี้ | วาดหน้าจอปกติ |

สังเกต `useState(undefined)` ตอนเริ่ม ไม่ใช่ `useState(null)` — ตั้งใจ

**ถ้ามีแค่สองสถานะจะเกิดอะไร** ลองคิดตามจังหวะเวลา:

```
0.00 วิ  รีเฟรชหน้า → user = null (ยังไม่ได้ถาม)
0.01 วิ  หน้าจอเห็น null → "ไม่ได้ล็อกอินนี่" → เด้งไปหน้าล็อกอิน  ← กระพริบ!
0.30 วิ  /me ตอบกลับมาว่าล็อกอินอยู่ → เด้งกลับ
```

ผู้ใช้จะเห็นหน้าล็อกอินแวบหนึ่งทุกครั้งที่รีเฟรช มี `undefined` คั่นไว้
หน้าจอจะรู้ว่า "ยังไม่ต้องตัดสินใจ รอก่อน"

**`useEffect(..., [])` ที่มีวงเล็บเหลี่ยมว่าง**

`[]` แปลว่า "รันครั้งเดียวตอนคอมโพเนนต์เกิด" ไม่รันซ้ำอีก —
เราอยากถาม `/me` แค่ครั้งเดียวตอนเปิดเว็บ

```jsx
if (!getToken()) { setUser(null); return; }   // ไม่มี token ก็ไม่ต้องถาม รู้เลยว่าไม่ได้ล็อกอิน
api("/auth/me").then(...).catch(() => setUser(null));   // มี token → ถามว่ายังใช้ได้ไหม
```

**`logout` เรียก `removeToken()` ไม่ใช่ `setToken(null)`** — เพราะ `setToken`
ในไฟล์ `api.js` มีหน้าที่เขียนอย่างเดียว การลบเป็นหน้าที่ของ `removeToken`
คนละฟังก์ชันกัน (เขียน `setToken(null)` จะได้ค่าเป็นข้อความ `"null"` ค้างไว้)

**`logout` ต้อง `queryClient.clear()` ด้วย — เรื่องความปลอดภัย ไม่ใช่ความสะอาด**

ข้อมูลที่ TanStack Query จำไว้ยังอยู่ในหน่วยความจำของแท็บ ถ้าไม่ล้าง:

```
admin เปิดหน้าสินค้า → cache จำ Lot ที่มีต้นทุนไว้ (เห็นได้เฉพาะ admin)
admin ออกจากระบบ → พนักงานล็อกอินต่อในแท็บเดิม → เปิดหน้าสินค้าเดียวกัน
→ เห็นต้นทุนจาก cache แวบหนึ่ง ก่อนข้อมูลใหม่จะมาทับ
```

`clear()` ลบทุกอย่างทิ้ง คนถัดไปเริ่มจากศูนย์

**`login` ไม่ต้องล้าง** เพราะก่อนหน้าจะล็อกอินได้ต้องผ่าน logout (ล้างแล้ว) หรือเพิ่งเปิดแอป
ส่วนกรณี token หมดอายุ `api.js` สั่ง `location.assign("/login")` ซึ่งโหลดหน้าใหม่ทั้งหน้า หน่วยความจำหายเองอยู่แล้ว

## 13. `src/components/Icon.jsx`

**ขั้นนี้ทำอะไร** ตัวแสดงไอคอน เรียกด้วยชื่อ `<Icon name="menu" />` แล้วได้รูป

**สร้างไฟล์ใหม่** `frontend/src/components/Icon.jsx`

```jsx
// Lucide icons (ISC license), copied as paths so no package is needed.
const PATHS = {
  wrench: <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />,
  menu: <><path d="M4 12h16" /><path d="M4 6h16" /><path d="M4 18h16" /></>,
  logout: <><path d="m16 17 5-5-5-5" /><path d="M21 12H9" /><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /></>,
};

export default function Icon({ name, size = 24, className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={`shrink-0 ${className}`}>
      {PATHS[name]}
    </svg>
  );
}
```

**อ่านโค้ดนี้ยังไง**

`PATHS` คือตารางที่จับคู่ **ชื่อ → รูปร่างเส้น** ส่วน `<Icon>` คือกรอบ `<svg>`
ที่เหมือนกันทุกไอคอน แล้วหยิบเส้นจากตารางมาใส่ตรงกลาง

```jsx
<Icon name="menu" />           → <svg>...เส้นสามเส้น...</svg>
<Icon name="wrench" size={30} />
```

ข้างใน `d="..."` คือพิกัดเส้น **ไม่ต้องอ่านเข้าใจ** ก็อปมาจาก lucide.dev ได้เลย

**ทำไมไม่ลง `lucide-react` ไปเลย**

ทั้งระบบใช้ไอคอนไม่กี่สิบตัว การก็อป path มาเองแปลว่า:
ไม่มีแพ็กเกจให้ตามอัปเดต · ไม่มีอะไรเพิ่มขนาดไฟล์ที่ผู้ใช้ต้องโหลด ·
**เติมเฉพาะตัวที่ได้ใช้จริง** (ทุกเฟสจะบอกว่าต้องเพิ่มตัวไหน)

**สามอย่างในแท็ก `<svg>` ที่มีเหตุผล**

- `stroke="currentColor"` — ไอคอนรับสีจากตัวหนังสือรอบ ๆ อัตโนมัติ
  วางในปุ่มสีขาวก็เป็นสีขาว วางในเมนูสีเทาก็เป็นสีเทา ไม่ต้องกำหนดทีละที่
- `aria-hidden="true"` — บอก screen reader ว่า "ข้ามไอคอนนี้ไป" เพราะเป็นของประดับ
  **ปุ่มที่มีแต่ไอคอนไม่มีข้อความ ต้องใส่ `aria-label` ที่ตัวปุ่มแทน**
  (เห็นตัวอย่างในข้อ 15: `aria-label="เปิดเมนู"`)
- `shrink-0` — ไอคอนไม่โดนบีบให้แบนเวลาข้อความข้าง ๆ ยาวจนล้น

## 14. `src/pages/LoginPage.jsx`

**ขั้นนี้ทำอะไร** หน้าจอจริงหน้าแรกของระบบ

**สร้างไฟล์ใหม่** `frontend/src/pages/LoginPage.jsx`

```jsx
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import Icon from "../components/Icon";

// หน้าเข้าสู่ระบบ ล็อกอินอยู่แล้วเด้งไป /
export default function LoginPage() {
  const { user, login } = useAuth();
  const { register, handleSubmit } = useForm({ defaultValues: { username: "", password: "" } });
  // ส่ง username/password ไป auth.login, ผิดโชว์ error
  const signIn = useMutation({ mutationFn: ({ username, password }) => login(username, password) });
  if (user) return <Navigate to="/" replace />;

  return (
    <main className="grid min-h-dvh place-items-center bg-surface px-4 py-8">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <div className="mx-auto mb-3 grid size-14 place-items-center rounded-2xl bg-accent text-white">
            <Icon name="wrench" size={30} />
          </div>
          <h1 className="text-2xl font-semibold">อู่ซ่อมรถ</h1>
          <p className="text-muted">เข้าสู่ระบบเพื่อเริ่มงาน</p>
        </div>
        <form onSubmit={handleSubmit((form) => signIn.mutate(form))} className="card space-y-4 p-6">
          <label className="block">
            <span className="label">ชื่อผู้ใช้</span>
            <input className="input" autoComplete="username" autoCapitalize="none" required {...register("username")} />
          </label>
          <label className="block">
            <span className="label">รหัสผ่าน</span>
            <input
              className="input"
              type="password"
              autoComplete="current-password"
              required
              {...register("password")}
            />
          </label>
          {signIn.error && (
            <p role="alert" className="field-error">
              {signIn.error.message}
            </p>
          )}
          <button className="btn btn-primary w-full" disabled={signIn.isPending}>
            {signIn.isPending ? "กำลังเข้าสู่ระบบ…" : "เข้าสู่ระบบ"}
          </button>
        </form>
      </div>
    </main>
  );
}
```

- **`<form onSubmit>` ไม่ใช่ `<button onClick>`** กด Enter ในช่องรหัสผ่านแล้วส่งได้

### อ่านโค้ดนี้ยังไง

**`if (user) return <Navigate to="/" replace />` — บรรทัดที่กันเปิดหน้าล็อกอินซ้ำ**

ล็อกอินอยู่แล้วแต่พิมพ์ `/login` เข้ามา → เด้งกลับหน้าแรกทันที
`replace` แปลว่า "แทนที่ประวัติหน้าเดิม" ไม่ใช่เพิ่มเข้าไป ผู้ใช้กด back
แล้วจะไม่วนกลับมาหน้าล็อกอินอีก

**ฟอร์มทุกฟอร์มในโปรเจกต์ใช้สองชิ้นนี้คู่กัน — จำรูปแบบนี้ครั้งเดียว**

```jsx
const { register, handleSubmit } = useForm({ defaultValues: {...} });   // ① ค่าในช่องกรอก
const signIn = useMutation({ mutationFn: (form) => ... });              // ② ส่งไป backend

<form onSubmit={handleSubmit((form) => signIn.mutate(form))}>           // ③ ต่อสองชิ้นเข้าด้วยกัน
  <input {...register("username")} />
  {signIn.error && ...signIn.error.message}
  <button disabled={signIn.isPending}>
```

**① `useForm` — react-hook-form เก็บค่าในช่องกรอกให้**

```jsx
<input {...register("username")} />
```

`register("username")` คืน `name` `ref` `onChange` `onBlur` มาให้ `{...}` กระจายใส่ `<input>`
ไม่ต้องมี `useState` ต่อช่อง ไม่ต้องเขียน `onChange={(e) => setForm({...form, username: e.target.value})}` ทุกช่อง
ฟอร์มสิบช่องก็เขียนสิบบรรทัด `register` เหมือนกันหมด

`defaultValues` คือค่าตั้งต้น (ฟอร์มแก้ไขข้อมูลส่งของเดิมเข้ามาตรงนี้ — เฟส 2)

**② `useMutation` — TanStack Query จัดการ "กำลังส่ง" และ "พัง" ให้**

| ได้อะไรมา | ใช้ทำอะไร |
|---|---|
| `signIn.mutate(ค่า)` | สั่งยิง |
| `signIn.isPending` | `true` ระหว่างรอ → ปิดปุ่ม กันกดซ้ำ · เปลี่ยนข้อความปุ่ม |
| `signIn.error` | `Error` ตัวล่าสุด (หรือ `null`) → โชว์ `error.message` |

ของที่เคยต้องเขียนเองทุกฟอร์ม (`useState` สำหรับ busy + error, `try/catch/finally`, ล้าง error เก่าก่อนลองใหม่,
ปลด busy ใน `finally` ไม่งั้นปุ่มค้าง) — `useMutation` ทำให้ครบ ลืมไม่ได้

**③ `handleSubmit` — ตัวต่อ**

`handleSubmit(fn)` คืนฟังก์ชันที่ใส่ `onSubmit` ได้ พอกดส่งมันจะ `preventDefault()` ให้ (กันหน้ารีเฟรช)
รวบค่าทุกช่องเป็น object `{ username, password }` แล้วส่งเข้า `fn`

> **ทำไมเขียน `(form) => signIn.mutate(form)` ไม่เขียน `handleSubmit(signIn.mutate)` ตรง ๆ**
> `handleSubmit` เรียก `fn(ค่า, event)` สองตัว แต่ `mutate` ถือว่าตัวที่สองคือตัวเลือกของมัน
> ส่ง event เข้าไปผิดที่ = บั๊กแปลก ๆ ห่อด้วยลูกศรให้ส่งแค่ตัวแรก ชัวร์กว่า

**`required` ยังใช้ของ HTML ตามเดิม** — เบราว์เซอร์กันช่องว่างให้ก่อน `handleSubmit` จะทำงาน
react-hook-form มีกฎตรวจของมันเอง (`register("x", { required: ... })`) แต่ระบบนี้ให้ backend (pydantic) เป็นคนตัดสิน
ฝั่งหน้าจอกันแค่ของพื้นฐานด้วย HTML พอ

**ไม่ต้องเขียนโค้ดว่า "ล็อกอินสำเร็จแล้วไปหน้าไหน"** — พอ `login()` สำเร็จ
มันไป `setUser()` ใน `auth.jsx` → `user` เปลี่ยน → React วาดใหม่ →
บรรทัด `if (user) return <Navigate .../>` ข้างบนทำงาน → เด้งเอง

**เรื่องเล็ก ๆ ที่ทำให้ใช้งานจริงได้ดีขึ้น**

- **ครอบ `<input>` ด้วย `<label>` ทั้งก้อน** — กดที่ข้อความป้ายแล้วเคอร์เซอร์
  เข้าช่องเลย (พื้นที่กดใหญ่ขึ้นมาก) และ screen reader อ่านออกว่าช่องนี้คืออะไร
  โดยไม่ต้องจับคู่ `id` กับ `htmlFor` ให้ยุ่ง
- **`disabled={signIn.isPending}`** — กันกดรัว ๆ ตอนเน็ตช้า ไม่งั้นยิง login ซ้ำหลายครั้ง
- **`autoComplete`** — ให้ตัวจัดการรหัสผ่านของเบราว์เซอร์ทำงานได้
- **`autoCapitalize="none"`** — มือถือชอบทำตัวแรกเป็นตัวใหญ่อัตโนมัติ
  ชื่อผู้ใช้ `admin` จะกลายเป็น `Admin` แล้วล็อกอินไม่ได้
- **`role="alert"`** — screen reader อ่านข้อความ error ทันทีที่โผล่
- **`min-h-dvh`** ไม่ใช่ `min-h-screen` — `dvh` คิดจากพื้นที่จริงบนมือถือ
  หลังหักแถบ URL ด้านบนออกแล้ว

## 15. `src/components/AppLayout.jsx` — แถบข้าง

**ขั้นนี้ทำอะไร** โครงหน้าจอที่ทุกหน้าในเฟสหลังจะอยู่ข้างใน — เมนูซ้ายบนจอคอม
ลิ้นชักบนมือถือ และช่องตรงกลางให้แต่ละหน้ามาแสดง

**สร้างไฟล์ใหม่** `frontend/src/components/AppLayout.jsx`

```jsx
import { useRef } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { ROLE_NAME, useAuth } from "../auth";
import Icon from "./Icon";

// เฟสหลังเติมกลุ่มและเมนูที่นี่  { to, label, icon, group, roles? }
export const GROUPS = [];
export const MENU = [];

// กรองเมนูตาม role ของผู้ใช้
export const menuFor = (role) => MENU.filter((m) => !m.roles || m.roles.includes(role));

// class ของลิงก์เมนู เปลี่ยนสีเมื่อเป็นหน้าปัจจุบัน
const linkClass = ({ isActive }) =>
  `flex min-h-11 w-full cursor-pointer items-center gap-3 rounded-lg px-3 text-sm transition-colors duration-150 ${
    isActive ? "bg-accent-soft font-semibold text-accent-ink" : "text-muted hover:bg-surface hover:text-ink"
  }`;

// เนื้อในแถบข้าง ใช้ร่วมกันทั้งจอใหญ่และลิ้นชักบนมือถือ
function SidebarContent({ user, logout }) {
  const items = menuFor(user.role);
  return (
    <>
      <div className="flex items-center gap-2 px-3 py-3 text-lg font-semibold">
        <Icon name="wrench" size={22} className="text-accent" />อู่ซ่อมรถ
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto">
        {GROUPS.map((g) => {
          const inGroup = items.filter((m) => m.group === g);
          if (inGroup.length === 0) return null;
          return (
            <div key={g} className="space-y-1">
              <div className="px-3 pb-1 text-xs text-muted">{g}</div>
              {inGroup.map((m) => (
                <NavLink key={m.to} to={m.to} className={linkClass}>
                  <Icon name={m.icon} /><span>{m.label}</span>
                </NavLink>
              ))}
            </div>
          );
        })}
      </div>
      <div className="space-y-1 border-t border-line pt-2">
        <div className="px-3 py-2 text-sm">
          <div className="truncate font-semibold">{user.full_name}</div>
          <div className="text-muted">{ROLE_NAME[user.role]}</div>
        </div>
        <button type="button" onClick={logout} className={linkClass({ isActive: false })}>
          <Icon name="logout" /><span>ออกจากระบบ</span>
        </button>
      </div>
    </>
  );
}

// โครงหลังล็อกอิน: แถบข้าง (จอใหญ่) / ลิ้นชัก (มือถือ) + <Outlet> แสดงหน้าย่อย
export default function AppLayout() {
  const { user, logout } = useAuth();
  const drawer = useRef(null);
  return (
    <div className="min-h-dvh md:flex">
      {/* จอใหญ่: แถบข้างอยู่กับที่ */}
      <nav aria-label="เมนูหลัก"
        className="sticky top-0 hidden h-dvh w-60 flex-none flex-col border-r border-line p-3 print:hidden md:flex">
        <SidebarContent user={user} logout={logout} />
      </nav>

      {/* มือถือ: แถบบน + ลิ้นชัก — <dialog> ให้ปุ่ม Esc พื้นหลังทึบ และกับดักโฟกัสมาเอง */}
      <header className="sticky top-0 z-20 flex items-center gap-2 border-b border-line bg-white px-2 py-2 print:hidden md:hidden">
        <button type="button" aria-label="เปิดเมนู" onClick={() => drawer.current.showModal()}
          className="grid size-11 cursor-pointer place-items-center rounded-lg text-muted hover:bg-surface hover:text-ink">
          <Icon name="menu" />
        </button>
        <span className="font-semibold">อู่ซ่อมรถ</span>
      </header>
      {/* คลิกที่ไหนก็ปิด ทั้งพื้นหลังและเมนูที่เพิ่งกด */}
      <dialog ref={drawer} aria-label="เมนูหลัก" onClick={() => drawer.current.close()}
        className="m-0 h-dvh max-h-none w-64 max-w-[80vw] flex-col bg-white p-3 backdrop:bg-black/40 open:flex md:hidden">
        <SidebarContent user={user} logout={logout} />
      </dialog>

      <main className="min-w-0 flex-1 p-4 md:p-6 print:p-0">
        <Outlet />
      </main>
    </div>
  );
}
```

### อ่านไฟล์นี้ยังไง — แบ่งเป็นสามชิ้น

```
SidebarContent   เนื้อในของเมนู (โลโก้ · รายการ · ชื่อผู้ใช้ · ออกจากระบบ)
                 เขียนครั้งเดียว ใช้สองที่ ↓
AppLayout        ├─ <nav>    จอใหญ่: แถบข้างซ้ายค้างไว้ตลอด
                 └─ <dialog> มือถือ: ลิ้นชักที่กดปุ่ม ☰ แล้วเลื่อนออกมา
```

```
จอใหญ่ (md: ขึ้นไป)                  มือถือ
┌────────┬──────────────────┐      ┌──────────────────┐
│ อู่ซ่อมรถ│                  │      │ ☰  อู่ซ่อมรถ      │ ← <header>
│        │                  │      ├──────────────────┤
│ (เมนู) │   <main>          │      │                  │
│        │   เนื้อหาแต่ละหน้า  │      │   <main>         │
│ ────── │                  │      │                  │
│ ชื่อผู้ใช้│                  │      │                  │
│ ออกจาก │                  │      │                  │
└────────┴──────────────────┘      └──────────────────┘
   <nav>                              กด ☰ → <dialog> เลื่อนออกมาทับ
```

**ทำไมต้องแยก `SidebarContent` ออกมาเป็นฟังก์ชัน** — แถบข้างกับลิ้นชักแสดงของ
เหมือนกันทุกอย่าง ถ้าเขียนสองรอบ วันที่เพิ่มเมนูใหม่ต้องจำว่าต้องแก้สองที่
(และจะลืมแก้ที่หนึ่งแน่นอน)

แต่มันใช้แค่ในไฟล์นี้ไฟล์เดียว เลยไม่ต้องแยกออกไปอยู่ `components/` ของตัวเอง

**`user` กับ `logout` ส่งเข้ามาเป็น prop ไม่ได้เรียก `useAuth()` ข้างใน**
`AppLayout` เรียก `useAuth()` ทีเดียวแล้วแจกให้ลูกทั้งสองที่ — ตัวลูกไม่ต้องรู้จัก
ระบบล็อกอินเลย รับแค่ข้อมูลที่ต้องใช้ ทดสอบและย้ายง่ายกว่า

**`const linkClass = ({ isActive }) => ...` — ฟังก์ชันที่คืน string ของคลาส**

`NavLink` ฉลาดพอที่จะเรียก `className` ให้เองพร้อมส่ง `{ isActive }` เข้าไป
(`isActive` = URL ตอนนี้ตรงกับลิงก์นี้ไหม) เมนูที่ตรงกับหน้าปัจจุบันเลยได้สีเน้นอัตโนมัติ

```jsx
<NavLink className={linkClass}>              // ส่งฟังก์ชันไป ให้ NavLink เรียกเอง
<button className={linkClass({ isActive: false })}>   // ปุ่มไม่ใช่ลิงก์ เรียกเองเลย
```

ปุ่มออกจากระบบไม่ใช่ `NavLink` ไม่มีใครเรียกให้ เลยต้องเรียกเองแล้วส่ง `false`
ไปตรง ๆ เพื่อให้หน้าตาเหมือนเมนูอื่น

**ลิ้นชักมือถือใช้ `<dialog>` — ท่าเดียวกับป๊อปอัพในเฟส 2**

`showModal()` เปิด แล้วเบราว์เซอร์แถมให้ฟรี: ฉากหลังมืด · กด Esc ปิด ·
กดของข้างหลังไม่ได้ · โฟกัสวนอยู่แต่ในลิ้นชัก

**`onClick` บน `<dialog>` สั่งปิดทุกการคลิก ไม่ได้เช็คว่าคลิกตรงไหน** — ตั้งใจ
เพราะในลิ้นชักมีแต่ลิงก์เมนู กดแล้วยังไงก็ต้องปิดอยู่แล้ว (ไม่งั้นหน้าเปลี่ยนแต่
ลิ้นชักยังบังอยู่) เขียนแบบนี้สั้นกว่าและครอบคลุมทั้งกดลิงก์และกดฉากหลัง

> (ป๊อปอัพฟอร์มในเฟส 2 ต่างออกไป — ที่นั่นต้องเช็ค `e.target` เพราะข้างในมีช่องกรอก
> ที่กดแล้วต้องไม่ปิด)

**ไม่ต้องมี state `open`** สั่งเปิดปิดผ่าน `drawer.current` ตรง ๆ ได้เลย
React ไม่ต้องรู้ด้วยซ้ำ เพราะไม่มีอะไรบนจอที่ต้องวาดใหม่ตามสถานะนี้

**`GROUPS` กับ `MENU` ยังว่างทั้งคู่ — ถูกแล้ว**

เฟสนี้ยังไม่มีหน้าไหนให้ไป เมนูเลยว่างเปล่า เฟสหลังค่อยเติมทีละบรรทัด:

```jsx
export const GROUPS = ["หน้าร้าน"];                                  // ← ชื่อกลุ่ม
export const MENU = [
  { to: "/stock", label: "สต็อก", icon: "box", group: "หน้าร้าน" },  // ← group ต้องตรงกับใน GROUPS
];
```

**สำคัญ: ทุกเมนูต้องมี `group` ที่ตรงกับสักตัวใน `GROUPS`** ไม่งั้น
`items.filter((m) => m.group === g)` หาไม่เจอ เมนูนั้นจะไม่โผล่บนจอเลย
และไม่มี error อะไรให้เห็นด้วย

**`roles` ใส่หรือไม่ใส่ก็ได้** ไม่ใส่ = ทุกคนเห็น · ใส่ = เฉพาะบทบาทในลิสต์
แต่ย้ำว่า **การกรองเมนูเป็นความสะดวกล้วน ๆ** ของจริงที่กันคือ `<Guard>` ใน
`main.jsx` และสิทธิ์ที่ backend (เฟส 2)

**เกร็ดเล็ก ๆ**

- `min-w-0` บน `<main>` — ยอมหดตอนมีตารางกว้าง แทนที่จะดันทั้งหน้าจนเลื่อนซ้ายขวาได้
- `print:hidden` — เมนูไม่ติดไปตอนสั่งพิมพ์ (เฟส 4 มีหน้าพิมพ์)
- `sticky top-0` — แถบข้างกับหัวมือถืออยู่กับที่ตอนเลื่อนเนื้อหา

## 16. `src/main.jsx` — แทนของเฟส 0

```jsx
import { QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./index.css";
import { queryClient } from "./api";
import { AuthProvider, useAuth } from "./auth";
import AppLayout from "./components/AppLayout";
import LoginPage from "./pages/LoginPage";

// กันหน้า: ยังโหลด user ไม่โชว์อะไร, ไม่ล็อกอินไป /login, role ไม่ตรงไป /
function Guard({ roles, children }) {
  const { user } = useAuth();
  if (user === undefined) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

createRoot(document.getElementById("root")).render(
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <Guard>
                <AppLayout />
              </Guard>
            }
          >
            <Route index element={<p className="text-muted">ยินดีต้อนรับ</p>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </QueryClientProvider>,
);
```

> หน้าตา `<Route element={<Guard><AppLayout /></Guard>}>` ที่แตกเป็นหลายบรรทัดคือผลของ Prettier
> ความหมายเหมือนเขียนบรรทัดเดียวทุกประการ

### อ่านโค้ดนี้ยังไง

**`Guard` — ด่านที่ทุกหน้า (ยกเว้นหน้าล็อกอิน) ต้องผ่าน**

```jsx
if (user === undefined) return null;        // ยังไม่รู้ → ยังไม่วาดอะไร
if (!user) return <Navigate to="/login" />; // ไม่ได้ล็อกอิน → ไล่ไปล็อกอิน
if (roles && !roles.includes(user.role))    // บทบาทไม่ตรง → กลับหน้าแรก
    return <Navigate to="/" replace />;
return children;                            // ผ่านหมด → วาดหน้าจริง
```

**บรรทัดแรกคือบรรทัดที่กันหน้ากระพริบ** — นี่คือที่ที่สถานะ `undefined`
จาก `auth.jsx` (ข้อ 12) ถูกใช้จริง ตัดบรรทัดนี้ทิ้งเมื่อไหร่ รีเฟรชทีไร
หน้าล็อกอินจะแวบขึ้นมาหนึ่งครั้งทุกครั้ง

`roles` เฟสนี้ยังไม่มีใครส่งมา แต่เขียนไว้ในตัวเดียวกันเลยเพื่อไม่ต้องมี
Guard สองแบบ (เฟส 2 จะใช้กันหน้าตั้งค่า)

**`replace` ใน `<Navigate>` — ลืมใส่แล้วปุ่ม back พัง**

`replace` แปลว่าแทนที่หน้าเดิมในประวัติเบราว์เซอร์ ไม่ใช่เพิ่มเข้าไป
ไม่ใส่แล้วผู้ใช้กด back จะวนกลับไปหน้าที่เพิ่งถูกไล่ออกมา แล้วถูกไล่ออกอีก วนไม่จบ

**`<Route element={...}>` ที่ไม่มี `path` เรียกว่า layout route**

```jsx
<Route element={<Guard><AppLayout /></Guard>}>   ← ไม่มี path
  <Route index element={...} />               ← ลูกทุกตัวได้ AppLayout ครอบ
  <Route path="*" element={...} />              และต้องผ่าน Guard
</Route>
```

เขียนแบบนี้ทีเดียว ทุกหน้าที่เพิ่มเข้าไปข้างในได้เมนูครอบและถูกกันไม่ให้เข้า
ถ้าไม่ได้ล็อกอิน โดยไม่ต้องเขียนซ้ำทีละหน้า

**`path="*"` คือ "URL อะไรก็ตามที่ไม่ตรงกับอันอื่น"** ส่งกลับหน้าแรก
ระบบใช้ภายในองค์กร ไม่ต้องทำหน้า 404 สวย ๆ

**ลำดับการครอบ: `QueryClientProvider` → `AuthProvider` → `BrowserRouter`**

- `QueryClientProvider` นอกสุด — ทุกคอมโพเนนต์ที่เรียก `useQuery` / `useMutation` ต้องอยู่ข้างใน
  (รวมถึง `LoginPage`) ส่ง `queryClient` ตัวเดียวกับที่ `auth.jsx` สั่ง `clear()` ตอน logout
- `AuthProvider` นอก `BrowserRouter` — context ต้องครอบทุกอย่างที่เรียก `useAuth()`
  ซึ่งรวมถึง `Guard` ที่อยู่ในชั้น route

---

## เช็คว่าเฟสนี้เสร็จ

### 1. คำสั่งต้องผ่านทั้งสองอัน

```
docker compose run --rm api pytest
docker compose exec -T web npm run build
```

อันแรกต้อง **passed ทั้งหมด ไม่มี failed** · อันที่สองต้องขึ้น **`✓ built`**

> **ระวัง: `npm run build` ผ่านไม่ได้แปลว่าโค้ดถูก** — vite ไม่ตรวจว่าตัวแปร
> ที่เรียกใช้มีจริงไหม พิมพ์ชื่อตัวแปรผิดจะผ่าน build แต่พอเปิดหน้าจะขาว
> ต้องเปิดเบราว์เซอร์ดูด้วยทุกครั้ง (ข้อ 2 ข้างล่าง)

### 2. ลองบนหน้าจอจริง

**ล็อกอิน**

- ล็อกอินด้วย `admin` กับรหัสจาก `.env` ได้
- **รีเฟรช (F5) แล้วยังล็อกอินอยู่ และหน้าล็อกอินต้องไม่แวบขึ้นมา**
  (ถ้าแวบ = `Guard` ไม่ได้เช็ค `undefined` — ย้อนไปข้อ 16)
- กรอกรหัสผิด → ขึ้น "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง" และ**หน้าไม่รีเฟรชทิ้ง**
  (ถ้ารีเฟรชทิ้ง = ลืมข้อยกเว้น `/auth/login` ใน `api.js` ข้อ 11)

**token หมดอายุ**

- DevTools (F12) → แท็บ Application → Local Storage → ลบ `token` → รีเฟรช
  → ต้องเด้งไปหน้าล็อกอิน

**มือถือ**

ย่อหน้าต่างให้แคบ หรือ F12 → กดไอคอนมือถือ

- แถบข้างซ้ายหายไป มีปุ่ม ☰ โผล่บนสุด
- กด ☰ → ลิ้นชักเลื่อนออกมา
- กดฉากหลัง หรือกด Esc → ปิด
- กดปุ่มออกจากระบบในลิ้นชัก → ออกได้

**ถ้าเจอหน้าขาว** เปิด DevTools → แท็บ Console อ่านบรรทัดแรกสุด
ส่วนใหญ่จะเป็น `X is not defined` ซึ่งบอกชื่อตัวแปรกับไฟล์ที่ผิดมาให้ตรง ๆ

## git

```
docker compose run --rm api ruff check --fix .
docker compose run --rm api ruff format .
docker compose exec -T web npm run format
git add -A && git commit -m "feat: login"
```
