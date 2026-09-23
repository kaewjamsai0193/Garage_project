# เฟส 1 — ฐาน + ล็อกอิน

**จบเฟสนี้:** ล็อกอินด้วย admin จาก `.env` ได้ · F5 แล้วยังอยู่ · ออกจากระบบได้ · จอคอมมีแถบเมนูซ้าย มือถือกด ☰ แล้วลิ้นชักเลื่อนออกมา

ตารางในฐาน: `users` ตารางเดียว

> โค้ดในไฟล์นี้คือของจริงใน repo ตอนจบเฟส 3 · ไฟล์ที่เฟสหลังเติมของ จะบอกไว้ใต้โค้ด

## ข้อมูลไหลยังไง

**ล็อกอิน**
```
LoginPage.jsx   useForm เก็บค่า → handleSubmit → signIn.mutate (useMutation)
  → auth.jsx:login → api.js POST /api/auth/login
  → users/auth_router.py:login
       select User ตามชื่อ → auth.py:verify_password (argon2) → auth.py:create_token
  ← { access_token, user }
  → localStorage เก็บ token · setUser(user) → ไปหน้า /
```

**ทุกคำขอหลังจากนี้**
```
api.js แนบ Authorization: Bearer <token>
  → auth.py:current_user   ถอด token → db.get(User, user_id) → ต้อง is_active
       ไม่ผ่านด้วยเหตุอะไรก็ตาม → 401 "กรุณาเข้าสู่ระบบ"
  → api.js เจอ 401 (ที่ไม่ใช่ /auth/login) → ลบ token → ไป /login
```

**F5 / เปิดเว็บใหม่** — `auth.jsx` ถาม `GET /api/auth/me` ด้วย token เดิม ([แผนที่ระบบ ข้อ 5](01-system-map.md))
**ออกจากระบบ** — `removeToken()` + `queryClient.clear()` + `setUser(null)`

## กฎหลัก

| กฎ | เพราะ |
|---|---|
| เก็บแค่ hash ของรหัสผ่าน (argon2) | ฐานหลุดก็ไม่ได้รหัสจริง |
| ชื่อผิด / รหัสผิด / บัญชีปิด ตอบ 401 **ข้อความเดียวกัน** | ไม่บอกคนนอกว่าบัญชีไหนมีจริง |
| token มีแค่ `user_id` + `exp` ไม่มี role | role อ่านจากฐานทุกคำขอ → ลดสิทธิ์/ปิดบัญชีมีผลทันที |
| JWT ใครก็อ่านได้ (แค่แก้ไม่ได้) | ห้ามใส่ความลับใน token |
| env อ่านด้วย `os.environ["X"]` | ลืมตั้ง → พังตั้งแต่เริ่ม ไม่ใช่ตอนมีคนกด |
| `JWT_SECRET` ว่าง/ค่าตัวอย่าง · `ADMIN_*` ว่าง/รหัสสั้น → ไม่ยอมเริ่ม | ค่าตัวอย่างอยู่ใน git ใครก็ปลอม token ได้ · admin รหัสว่างใครก็เข้าได้ |
| `user` ฝั่งหน้าจอมี 3 สถานะ | แยก "กำลังเช็ค" ออกจาก "ไม่ได้ล็อกอิน" ไม่งั้น F5 แล้วเด้งไปหน้า login แวบหนึ่ง |

---

# backend

## `app/db.py` — ต่อฐาน

```python
import os

from fastapi import HTTPException
from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

engine = create_engine(os.environ["DATABASE_URL"])
SessionLocal = sessionmaker(engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def get_db():
    """Dependency: เปิด DB session ให้ endpoint แล้วปิดเองเมื่อจบ request"""
    with SessionLocal() as db:
        yield db
```

- `expire_on_commit=False` หลัง commit ยังอ่านค่าใน object ได้ (คืนให้ response ได้เลย ไม่ต้องโหลดใหม่)
- `autoflush=False` ไม่แอบส่ง SQL ก่อนเราสั่ง
- `naming_convention` ตั้งชื่อ constraint ให้เดาได้ (`ck_users_role`) — migration ภายหลังสั่ง drop/แก้ตามชื่อได้ (เฟส 4 ใช้จริง)
- `get_db` ใช้ `yield` → FastAPI เปิด session ให้หนึ่งอันต่อคำขอ แล้วปิดเองตอนจบ (พังกลางทางก็ rollback)
- `get_or_404` มาเฟส 2 · `lock_shop` มาเฟส 3

## `app/models.py` — ตาราง `users`

```python
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

- `Mapped[str]` ไม่มี `| None` = `NOT NULL`
- เวลาเก็บแบบมีโซนเสมอ (`timezone=True`) — เวลาไม่มีโซนคือระเบิดเวลา
- `CheckConstraint` ให้ฐานกันค่าผิดอีกชั้น (role ต้องเป็น 3 ค่านี้) ต่อให้โค้ดพลาดก็ไม่มีข้อมูลเสียเข้าฐาน
- `server_default` = ฐานใส่ค่าให้เอง (ใช้ได้แม้ insert จากนอกโค้ด)

สร้าง migration แล้ว**เปิดอ่านไฟล์ที่ได้ทุกครั้ง**ก่อน upgrade

```
docker compose exec api alembic revision --autogenerate -m "users"
docker compose exec api alembic upgrade head
```

## `app/auth.py` — รหัสผ่าน + token + ตรวจบัตร

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
if JWT_SECRET in ("", "change-me-to-a-long-random-string"):
    raise RuntimeError("ตั้ง JWT_SECRET ใน .env เป็นข้อความสุ่มยาว ๆ ก่อน (ห้ามใช้ค่าตัวอย่าง)")
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
            pass  # token เสีย/หมดอายุ/ไม่มี user_id → user ยังเป็น None ไปจบที่ 401 ข้างล่างที่เดียว
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบ")
    return user
```

- `PasswordHash.recommended()` = Argon2id · salt สุ่มต่อครั้ง รหัสเดียวกัน hash ไม่ซ้ำ
- `create_token` → `{user_id, exp}` เซ็นด้วย `JWT_SECRET` · `exp` ชื่อมาตรฐาน PyJWT เช็คหมดอายุให้เอง
- `current_user` ตั้ง `user = None` ไว้ก่อน ทุกกรณีที่ไม่ผ่าน (ไม่มี token · เสีย · หมดอายุ · ไม่มี user · บัญชีปิด) ไปจบที่ `raise 401` จุดเดียว
- `HTTPBearer(auto_error=False)` ไม่ให้มันตอบ 403 เอง — เราอยากได้ 401 ข้อความไทย
- `require_role` · `admin` · `staff` มาเฟส 2–3

## `app/schemas.py` — แม่ของ schema ทุกตัว

```python
from pydantic import BaseModel, ConfigDict


class In(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

- `In` ขาเข้า: ตัดช่องว่างหัวท้ายทุกข้อความ (`"  admin "` = `"admin"`)
- `Out` ขาออก: อ่านค่าจาก object ของ SQLAlchemy ได้ตรง ๆ
- `serialize_for_role` มาเฟส 3

## `app/users/schemas.py`

```python
from typing import Literal

from pydantic import BaseModel, Field

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

`UserOut` ไม่มี `password_hash` = ด่านกันรหัสรั่ว ส่งอะไรออกไปก็ผ่าน schema นี้ · `UserCreate` / `UserUpdate` มาเฟส 2

## `app/users/service.py` — admin คนแรก

```python
import os

from fastapi import HTTPException
from sqlalchemy import select

from app.auth import hash_password
from app.db import SessionLocal, get_or_404
from app.models import User


def ensure_admin():
    """ถ้า DB ยังไม่มี admin เลย สร้างจาก env ADMIN_USERNAME/ADMIN_PASSWORD (เรียกจาก lifespan), ค่าว่าง/รหัสสั้น → ไม่ยอมเริ่มระบบ"""
    with SessionLocal() as db:
        admin_user = db.scalar(select(User).where(User.role == "admin"))
        if admin_user is None:
            username, password = os.environ["ADMIN_USERNAME"].strip(), os.environ["ADMIN_PASSWORD"]
            if not username or len(password) < 6:
                raise RuntimeError("ตั้ง ADMIN_USERNAME และ ADMIN_PASSWORD (อย่างน้อย 6 ตัว) ใน .env ก่อนเริ่มระบบ")
            db.add(User(username=username, full_name="ผู้ดูแลระบบ", role="admin", password_hash=hash_password(password)))
            db.commit()
```

- ระบบใหม่ไม่มีใครล็อกอินได้ → สร้าง admin จาก `.env` ตอนเริ่ม
- เช็ค "**ไม่มี admin เลย**" ไม่ใช่ "ไม่มีชื่อนี้" — ไม่งั้นปิดบัญชีตั้งต้นทิ้งแล้วมันโผล่กลับทุกครั้งที่รีสตาร์ท (บัญชีที่ปิดยังนับว่ามี)
- ค่าว่าง/รหัสสั้น → `RuntimeError` api ไม่ขึ้น `docker compose logs api` บอกให้แก้อะไร
- เปิด session เองเพราะถูกเรียกตอนเริ่มแอป ไม่มีคำขอ ไม่มี `Depends`

## `app/users/auth_router.py`

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
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    return {"access_token": create_token(user.id), "user": user}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    """GET /api/auth/me: คืนข้อมูลผู้ใช้เจ้าของ token (frontend ใช้ตอนเปิดแอป)"""
    return user
```

- router **อ่าน**ข้อมูลเองได้ (`select`) แต่**เขียน**ต้องผ่าน service เท่านั้น
- `/auth/me` ให้หน้าจอถามตอนเปิดเว็บใหม่ว่า token เดิมยังใช้ได้ไหม และตอนนี้ข้อมูลเราเป็นยังไง

## `app/main.py`

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.settings import router as settings
from app.stock import router as stock
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
app.include_router(stock.router)


@app.exception_handler(IntegrityError)
def handle_integrity_error(_request, _exc):
    """แปลง IntegrityError จาก DB (ชน unique/check) → HTTP 409 ข้อความไทย"""
    return JSONResponse(status_code=409, content={"detail": "ข้อมูลขัดกับกฎของระบบ"})


@app.get("/api/health")
def health():
    """GET /api/health: เช็คว่าเซิร์ฟเวอร์ยังทำงาน"""
    return {"ok": True}
```

- `lifespan` โค้ดที่รันตอนแอปเริ่ม → `ensure_admin()`
- `IntegrityError` (ชน unique/CHECK ที่ฐาน) → 409 ข้อความไทย แทน 500
- router ของ users/settings/stock มาเฟส 2–3

## `tests/conftest.py` — ของใช้ร่วมทุกเทสต์

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
        conn.execute(text("insert into settings (id) values (1)"))  # truncate ล้างแถวที่ migration ใส่ไว้


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
def headers(users):
    return {r: {"Authorization": f"Bearer {create_token(u.id)}"} for r, u in users.items()}


@pytest.fixture
def make_product():
    def make(code="P1", unit="ชิ้น", sale_price="100"):
        with SessionLocal() as s:
            p = models.Product(code=code, name=f"สินค้า {code}", unit=unit, sale_price=sale_price)
            s.add(p)
            s.commit()
            return p.id

    return make
```

- **3 บรรทัดแรกสำคัญที่สุด:** ตั้ง `DATABASE_URL` เป็นฐานเทสต์**ก่อน** import app — สลับลำดับแล้วเทสต์ล้างข้อมูลจริง
- `clean` (autouse) ล้างทุกตารางก่อนทุกเทสต์ แล้วใส่แถว settings กลับ
- `users` สร้าง 3 บทบาท รหัส `pw` · `headers` = header ของแต่ละบทบาท (`headers["admin"]`) · `make_product` มาเฟส 3

## `tests/test_auth.py`

```python
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select

from app import models
from app.auth import JWT_SECRET, create_token, current_user, hash_password, verify_password
from app.db import SessionLocal
from app.users.service import ensure_admin


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
    assert hash_password("secret1") != hash_password("secret1")  # salt สุ่มต่อครั้ง


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


# --- API: /api/auth ---


def login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def test_login_and_me(client, users):
    r = login(client, "admin", "pw")
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["role"] == "admin" and "password_hash" not in body["user"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}).json()
    assert me["username"] == "admin" and "password_hash" not in me


def test_login_strips_spaces_around_username(client, users):
    assert login(client, "  admin ", "pw").status_code == 200  # In ตัดช่องว่างหัวท้าย


def test_wrong_password(client, users):
    r = login(client, "admin", "nope")
    assert r.status_code == 401 and r.json()["detail"] == "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"


def test_unknown_user_and_inactive_user_same_message_as_wrong_password(client, users):
    with SessionLocal() as s:
        s.get(models.User, users["employee"].id).is_active = False
        s.commit()
    wrong = login(client, "admin", "nope").json()
    assert login(client, "nobody", "pw").json() == wrong  # ไม่บอกว่าชื่อนี้ไม่มี
    assert login(client, "employee", "pw").json() == wrong  # ไม่บอกว่าบัญชีถูกปิด


def test_login_needs_both_fields(client):
    assert client.post("/api/auth/login", json={"username": "admin"}).status_code == 422


def test_me_needs_token(client, headers):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=headers["mechanic"]).json()["username"] == "mechanic"


# --- ensure_admin ---


def usernames():
    with SessionLocal() as s:
        return sorted(u.username for u in s.scalars(select(models.User)))


def admin_env(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "owner")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret99")


def test_ensure_admin_creates_once_on_empty_db(monkeypatch, client):
    admin_env(monkeypatch)
    ensure_admin()
    ensure_admin()
    assert usernames() == ["owner"]
    assert login(client, "owner", "secret99").status_code == 200


def test_ensure_admin_skips_when_an_admin_exists(monkeypatch, users):
    admin_env(monkeypatch)
    ensure_admin()
    assert "owner" not in usernames()


def test_ensure_admin_creates_when_only_non_admins_exist(monkeypatch):
    admin_env(monkeypatch)
    with SessionLocal() as s:
        s.add(models.User(username="mech", full_name="ช่าง", role="mechanic", password_hash=hash_password("x")))
        s.commit()
    ensure_admin()
    assert usernames() == ["mech", "owner"]


@pytest.mark.parametrize(
    ("username", "password"), [("", "secret99"), ("  ", "secret99"), ("owner", ""), ("owner", "12345")]
)
def test_ensure_admin_refuses_blank_or_short_env(monkeypatch, username, password):
    monkeypatch.setenv("ADMIN_USERNAME", username)
    monkeypatch.setenv("ADMIN_PASSWORD", password)
    with pytest.raises(RuntimeError, match="ADMIN_USERNAME"):
        ensure_admin()
    assert usernames() == []  # ไม่มี admin ชื่อว่าง/รหัสว่างหลุดเข้าฐาน
```

- `rejected()` ตัวช่วย: ต้องได้ 401 ข้อความไทยเสมอ ห้าม 500 ห้ามได้ user
- เทสต์ `current_user` ทุกกรณีปฏิเสธ (ไม่มี header · ขยะ · คนละ secret · หมดอายุ · ไม่มี user_id · user หายไป · บัญชีปิด)
- ยิง API: login/me · ชื่อผิดกับรหัสผิดได้ข้อความเดียวกัน · `ensure_admin` สร้างครั้งเดียว / ข้ามเมื่อมี admin / ปฏิเสธค่าว่าง

---

# หน้าจอ

## `src/index.css` — สีและคลาสกลาง (ทั้งไฟล์ ณ จบเฟส 3)

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
  body {
    @apply bg-white text-ink antialiased;
  }
  :focus-visible {
    @apply outline-2 outline-offset-2 outline-accent;
  }
  @media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
      transition: none !important;
      animation: none !important;
    }
  }
}

@layer components {
  .page-title {
    @apply text-xl font-semibold lg:text-2xl;
  }
  .card {
    @apply rounded-xl border border-line bg-white p-4;
  }
  .label {
    @apply mb-1 block text-sm text-muted;
  }
  .field-hint {
    @apply mt-1 block text-sm text-muted;
  }
  .field-error {
    @apply text-sm font-medium text-danger;
  }
  .input {
    @apply min-h-11 w-full rounded-lg border border-line bg-white px-3 py-2 text-base transition-colors duration-150 focus:border-accent focus:ring-3 focus:ring-accent-soft focus:outline-none disabled:bg-surface disabled:text-muted;
  }

  .btn {
    @apply inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-lg px-4 font-semibold whitespace-nowrap transition duration-150 disabled:cursor-not-allowed disabled:opacity-50;
  }
  .btn-primary {
    @apply bg-accent text-white hover:bg-accent-ink;
  }
  .btn-secondary {
    @apply border border-line bg-white text-ink hover:bg-surface;
  }
  .btn-ghost {
    @apply text-ink hover:bg-surface;
  }
  .btn-icon {
    @apply min-w-11 px-0;
  }

  .tabs {
    @apply flex gap-1 overflow-x-auto border-b border-line;
  }
  .tab {
    @apply -mb-px inline-flex min-h-11 cursor-pointer items-center border-b-2 border-transparent px-3 text-sm font-medium whitespace-nowrap text-muted transition-colors duration-150 hover:text-ink aria-selected:border-accent aria-selected:text-ink aria-[current=page]:border-accent aria-[current=page]:text-ink;
  }

  .modal {
    @apply mx-0 mt-auto mb-0 max-h-[92dvh] w-full max-w-none rounded-t-2xl bg-white p-0 text-ink backdrop:bg-ink/40 md:m-auto md:max-h-[90dvh] md:w-[calc(100%-2rem)] md:max-w-[560px] md:rounded-xl;
  }
  .modal[open] {
    @apply flex flex-col;
  }

  .table {
    @apply w-full text-sm;
  }
  .table th {
    @apply border-b border-line bg-surface px-3 py-2.5 text-left font-medium whitespace-nowrap text-muted;
  }
  .table td {
    @apply border-b border-line px-3 py-3 align-middle;
  }
  .table tbody tr {
    @apply cursor-pointer transition-colors duration-150 hover:bg-surface;
  }

  .badge {
    @apply inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap;
  }
  .badge-neutral {
    @apply bg-neutral-soft text-ink;
  }
  .badge-info {
    @apply bg-accent-soft text-accent-ink;
  }
  .badge-warn {
    @apply bg-warn-soft text-warn-ink;
  }
  .badge-ok {
    @apply bg-ok-soft text-ok-ink;
  }
  .badge-danger {
    @apply bg-danger-soft text-danger;
  }

  .num {
    font-variant-numeric: tabular-nums;
  }
}
```

- `@theme` ประกาศสีครั้งเดียว ได้คลาส `bg-accent` `text-muted` ใช้ทั้งระบบ — ห้ามเขียน hex ในคอมโพเนนต์
- `.btn` = รูปทรง · `.btn-primary` / `-secondary` / `-ghost` = สี ใส่คู่กันเสมอ · `.btn-icon` ปุ่มไอคอนล้วนกว้างอย่างน้อย 44px
- `min-h-11` (44px) ทุกอย่างที่กดได้ — ขนาดนิ้วกดไม่พลาด
- `:focus-visible` เห็นชัดสำหรับคนใช้ Tab · `prefers-reduced-motion` ปิดแอนิเมชันให้คนที่ตั้งไว้
- `.modal` `.table` `.badge-*` `.tabs` เติมเฟส 2

## `src/api.js` — ที่เดียวที่คุยกับ backend

```js
import { QueryClient } from "@tanstack/react-query";
import axios from "axios";

// token ใน localStorage: อ่าน / เก็บ / ลบ
export const getToken = () => localStorage.getItem("token");
export const setToken = (token) => localStorage.setItem("token", token);
export const removeToken = () => localStorage.removeItem("token");

// แปลง error validation 1 รายการจาก FastAPI (422) → ข้อความไทย
function validationMessage({ type, ctx = {} }) {
  const messages = {
    missing: "กรอกข้อมูลไม่ครบ",
    greater_than: `ต้องมากกว่า ${ctx.gt}`,
    greater_than_equal: `ต้องไม่น้อยกว่า ${ctx.ge}`,
    less_than: `ต้องน้อยกว่า ${ctx.lt}`,
    less_than_equal: `ต้องไม่เกิน ${ctx.le}`,
    string_too_short: "ข้อความสั้นเกินไป",
    string_too_long: "ข้อความยาวเกินไป",
  };
  return messages[type] ?? "รูปแบบข้อมูลไม่ถูกต้อง";
}

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

- ทุกหน้าเรียก `api()` ไม่มีใครเรียก axios เอง — แนบ token / แปลง error / จัดการ 401 อยู่ที่เดียว
- error มีสองแบบ: `detail` เป็นข้อความ (เราโยนเอง) หรือรายการ (422 จาก pydantic) → แปลงเป็นไทย
- 401 ที่ไม่ใช่หน้าล็อกอิน → ลบ token แล้วไป `/login` (ยกเว้น `/auth/login` ไม่งั้นรหัสผิดแล้วหน้ารีโหลดแทนที่จะโชว์ข้อความ)
- `queryClient`: `queryFn` กลางแปลงกุญแจเป็น path (`["products", 5, "lots"]` → `GET /products/5/lots`) · `retry: false` เพราะ 404/403 ลองซ้ำก็เหมือนเดิม
- `plainNumber` เติมเฟส 2 · `formatMoney` ฯลฯ เติมเฟส 3

## `src/auth.jsx` — ใครล็อกอินอยู่

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
  return <AuthContext.Provider value={{ user, setUser, login, logout }}>{children}</AuthContext.Provider>;
}

// ดึง { user, setUser, login, logout } จาก AuthContext (setUser ใช้ตอน admin แก้บัญชีตัวเอง)
export const useAuth = () => useContext(AuthContext);
```

| `user` | ความหมาย |
|---|---|
| `undefined` | กำลังเช็ค `/auth/me` |
| `null` | ไม่ได้ล็อกอิน |
| object | ล็อกอินแล้ว |

- `logout` ต้อง `queryClient.clear()` — กันคนถัดไปในเครื่องเดียวกันเห็นข้อมูลค้าง (เช่นต้นทุนที่เห็นเฉพาะ admin)
- `setUser` ใน context เติมเฟส 2 (admin แก้ชื่อตัวเองแล้วแถบข้างเปลี่ยนตาม)

## `src/components/Icon.jsx`

```jsx
// ไอคอน SVG ตามชื่อใน PATHS
export default function Icon({ name, size = 24, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={`shrink-0 ${className}`}
    >
      {PATHS[name]}
    </svg>
  );
}
```

`PATHS` ด้านบนของไฟล์เก็บเส้น SVG ตามชื่อ (`menu` `logout` `box` …) เติมเฉพาะตัวที่ใช้จริง ไม่ลง icon library ทั้งชุด

## `src/pages/LoginPage.jsx` — แบบของทุกฟอร์มในระบบ

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

```
useForm        เก็บค่าที่พิมพ์ ({...register("username")})
useMutation    สถานะ "กำลังส่ง" (isPending) + error ให้เอง
handleSubmit   รวบค่าทั้งฟอร์ม → mutate(form)
```

- ล็อกอินอยู่แล้วเปิดหน้านี้ → `<Navigate to="/">` · ล็อกอินสำเร็จ `user` เปลี่ยน → บรรทัดเดียวกันพาไปเอง
- `required` ของ HTML กันช่องว่างตั้งแต่เบราว์เซอร์ · `autoComplete` ให้ตัวจัดการรหัสผ่านเติมให้

## `src/components/AppLayout.jsx` — แถบข้าง / ลิ้นชัก

```jsx
import { useRef } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { ROLE_NAME, useAuth } from "../auth";
import Icon from "./Icon";

// เฟสหลังเติมกลุ่มและเมนูที่นี่  { to, label, icon, group } — group ต้องตรงกับชื่อใน GROUPS
const GROUPS = ["คลังสินค้า"];
const MENU = [{ to: "/stock", label: "สต็อก", icon: "box", group: "คลังสินค้า" }];

// class ของลิงก์เมนู เปลี่ยนสีเมื่อเป็นหน้าปัจจุบัน
const linkClass = ({ isActive }) =>
  `flex min-h-11 w-full cursor-pointer items-center gap-3 rounded-lg px-3 text-sm transition-colors duration-150 ${
    isActive ? "bg-accent-soft font-semibold text-accent-ink" : "text-muted hover:bg-surface hover:text-ink"
  }`;

// เนื้อในแถบข้าง ใช้ร่วมกันทั้งจอใหญ่และลิ้นชักบนมือถือ
function SidebarContent({ user, logout }) {
  return (
    <>
      <div className="flex items-center gap-2 px-3 py-3 text-lg font-semibold">
        <Icon name="wrench" size={22} className="text-accent" />
        อู่ซ่อมรถ
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto">
        {GROUPS.map((group) => (
          <div key={group} className="space-y-1">
            <div className="px-3 pb-1 text-xs text-muted">{group}</div>
            {MENU.filter((m) => m.group === group).map((m) => (
              <NavLink key={m.to} to={m.to} className={linkClass}>
                <Icon name={m.icon} />
                <span>{m.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </div>
      <div className="space-y-1 border-t border-line pt-2">
        {user.role === "admin" && (
          <NavLink to="/settings" className={linkClass}>
            <Icon name="settings" />
            <span>ตั้งค่า</span>
          </NavLink>
        )}
        <div className="px-3 py-2 text-sm">
          <div className="truncate font-semibold">{user.full_name}</div>
          <div className="text-muted">{ROLE_NAME[user.role]}</div>
        </div>
        <button type="button" onClick={logout} className={linkClass({ isActive: false })}>
          <Icon name="logout" />
          <span>ออกจากระบบ</span>
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
      <nav
        aria-label="เมนูหลัก"
        className="sticky top-0 hidden h-dvh w-60 flex-none flex-col border-r border-line p-3 print:hidden md:flex"
      >
        <SidebarContent user={user} logout={logout} />
      </nav>

      {/* มือถือ: แถบบน + ลิ้นชัก — <dialog> ให้ปุ่ม Esc พื้นหลังทึบ และกับดักโฟกัสมาเอง */}
      <header className="sticky top-0 z-20 flex items-center gap-2 border-b border-line bg-white px-2 py-2 print:hidden md:hidden">
        <button
          type="button"
          aria-label="เปิดเมนู"
          onClick={() => drawer.current.showModal()}
          className="grid size-11 cursor-pointer place-items-center rounded-lg text-muted hover:bg-surface hover:text-ink"
        >
          <Icon name="menu" />
        </button>
        <span className="font-semibold">อู่ซ่อมรถ</span>
      </header>
      {/* คลิกที่ไหนก็ปิด ทั้งพื้นหลังและเมนูที่เพิ่งกด */}
      <dialog
        ref={drawer}
        aria-label="เมนูหลัก"
        onClick={() => drawer.current.close()}
        className="m-0 h-dvh max-h-none w-64 max-w-[80vw] flex-col bg-white p-3 backdrop:bg-black/40 open:flex md:hidden"
      >
        <SidebarContent user={user} logout={logout} />
      </dialog>

      <main className="min-w-0 flex-1 p-4 md:p-6 print:p-0">
        <Outlet />
      </main>
    </div>
  );
}
```

- `SidebarContent` ใช้ร่วมสองที่: แถบข้างจอใหญ่ + ลิ้นชัก `<dialog>` บนมือถือ (Esc ปิด · ฉากหลังมืด · โฟกัสวนในลิ้นชัก ได้ฟรีจากเบราว์เซอร์)
- คลิกตรงไหนในลิ้นชักก็ปิด (รวมเมนูที่เพิ่งกด)
- เมนูมาจาก `GROUPS` + `MENU` — **`group` ต้องตรงชื่อใน `GROUPS`** ไม่งั้นเมนูไม่โผล่และไม่มี error (เมนูสต็อกเติมเฟส 3)
- ลิงก์ตั้งค่าโชว์เฉพาะ admin

## `src/main.jsx` — route ทั้งหมด (ณ จบเฟส 3)

```jsx
import { QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./index.css";
import { queryClient } from "./api";
import { AuthProvider, useAuth } from "./auth";
import AppLayout from "./components/AppLayout";
import LoginPage from "./pages/LoginPage";
import ProductDetailPage from "./pages/ProductDetailPage";
import ProductFormPage from "./pages/ProductFormPage";
import ProductListPage from "./pages/ProductListPage";
import SettingsPage from "./pages/SettingsPage";
import UserFormPage from "./pages/UserFormPage";
import UserListPage from "./pages/UserListPage";

const STAFF = ["admin", "employee"];
const ADMIN = ["admin"];

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
            <Route index element={<Navigate to="/stock" replace />} />
            <Route path="stock" element={<ProductListPage />}>
              <Route
                path="new"
                element={
                  <Guard roles={STAFF}>
                    <ProductFormPage />
                  </Guard>
                }
              />
            </Route>
            <Route path="stock/:id" element={<ProductDetailPage />} />
            <Route
              path="settings"
              element={
                <Guard roles={ADMIN}>
                  <SettingsPage />
                </Guard>
              }
            />
            <Route
              path="settings/users"
              element={
                <Guard roles={ADMIN}>
                  <UserListPage />
                </Guard>
              }
            >
              <Route path="new" element={<UserFormPage />} />
              <Route path=":id" element={<UserFormPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </QueryClientProvider>,
);
```

- ครอบ `QueryClientProvider → AuthProvider → BrowserRouter` (auth ใช้ queryClient · route ใช้ auth)
- `Guard`: ยังเช็ค user อยู่ → ไม่วาด · ไม่ล็อกอิน → `/login` · บทบาทไม่ตรง → `/`
- `<Navigate replace>` ไม่ทิ้งหน้าที่ถูกเด้งไว้ในประวัติ (ไม่งั้นกด back แล้ววนกลับมา)
- `<Route element={...}>` ไม่มี `path` = layout route: ทุกหน้าข้างในได้ `AppLayout` ครอบ
- route ตั้งค่า/ผู้ใช้เติมเฟส 2 · สต็อกเติมเฟส 3

---

## เช็คว่าเสร็จ

- pytest เขียว · `npm run build` ผ่าน
- ล็อกอินถูก → เข้าได้ · รหัสผิด → ข้อความแดง · F5 แล้วไม่หลุด · ออกจากระบบแล้วกด back ไม่กลับเข้าได้
- ย่อจอเป็นมือถือ → ☰ เปิดลิ้นชัก · Esc ปิดได้
