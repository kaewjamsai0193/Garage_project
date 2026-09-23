# เฟส 2 — ผู้ใช้ + ค่าตั้ง

**จบเฟสนี้:** admin สร้าง / แก้ / ปิดบัญชีพนักงานกับช่างได้ · ตั้งชื่ออู่ ที่อยู่ เลขผู้เสียภาษี อัตรา VAT ได้ · ช่างเข้าหน้าตั้งค่าไม่ได้จริง (กันทั้งจอและ API)

ตารางใหม่: `settings` (แถวเดียวตลอดชีวิตระบบ `id = 1`)

เฟสนี้สร้าง**ของกลางที่ทุกเฟสหลังใช้ซ้ำ**: ป๊อปอัพ · หน้ารายการ · ตาราง/การ์ด · ป้ายสถานะ · ช่องกรอก

> โค้ดในไฟล์นี้คือของจริงใน repo ตอนจบเฟส 3

## ข้อมูลไหลยังไง

**เปิดรายชื่อผู้ใช้**
```
/settings/users → UserListPage   useQuery(["users"]) → GET /api/users (admin)
  → ListLayout (หัว + ปุ่มเพิ่ม) → DataTable (จอแคบ = การ์ด · จอกว้าง = ตาราง)
```

**กดผู้ใช้คนหนึ่ง → ป๊อปอัพแก้**
```
/settings/users/5 = route ลูกของ UserListPage → ListLayout วาด <Outlet> พร้อมส่ง close()
  → UserFormPage   หา user id 5 จาก cache ["users"] (ไม่ต้องรอโหลด)
  → UserForm       key={id} · useForm(defaultValues)
  → บันทึก: PATCH /api/users/5 → users/service.py:update_user
     → invalidate ["users"] · ถ้าแก้บัญชีตัวเอง setUser(saved) → close() กลับ /settings/users
  → ปิด/เปิดใช้งาน: PATCH { is_active } → invalidate ["users"] (ป๊อปอัพยังเปิดอยู่)
```

**ค่าตั้งอู่**
```
/settings → SettingsPage   useQuery(["settings"]) → GET /api/settings (ทุกคนที่ล็อกอิน)
  → SettingsForm → PUT /api/settings (admin) → settings/service.py:update_settings
  → setQueryData(["settings"], ค่าที่ตอบกลับ) ไม่ต้อง GET ซ้ำ
```

## กฎหลัก

| กฎ | เพราะ |
|---|---|
| 401 = ไม่รู้ว่าเป็นใคร · 403 = รู้แต่ไม่มีสิทธิ์ | `current_user` ตรวจก่อน `require_role` ค่อยตรวจบทบาท |
| ไม่มีการลบผู้ใช้ มีแต่ปิดใช้งาน | เอกสารเก่ายังอ้างชื่อคนนั้นอยู่ |
| admin ปิดหรือลดสิทธิ์ตัวเองไม่ได้ | ระบบต้องมี admin เหลืออย่างน้อยหนึ่งคนเสมอ |
| ค่าตั้งเก็บในฐาน แถวเดียว | เจ้าของอู่แก้เองได้ ไม่ต้องแก้โค้ด |
| ซ่อนเมนูตามบทบาท = ความสะดวก | ด่านจริงคือ backend |
| ป๊อปอัพเพิ่ม/แก้ = route ลูก (มี URL) | ส่งลิงก์ / F5 แล้วยังเปิดอยู่ |

---

# backend

## `app/db.py` — เติม `get_or_404`

```python
def get_or_404(db, model, id, label):
    """ดึงแถวจาก DB ตาม id ถ้าไม่เจอโยน 404 ไม่พบ{label}"""
    obj = db.get(model, id)
    if obj is None:
        raise HTTPException(404, f"ไม่พบ{label}")
    return obj
```

endpoint ที่รับ id จาก URL ใช้ตัวนี้ตัวเดียว ไม่เจอได้ "ไม่พบ{label}" มาตรฐานเดียวทั้งระบบ

## `app/auth.py` — เติม `require_role` + `admin`

```python
def require_role(*roles):
    """สร้าง Dependency ที่เช็ค role ของ current_user, ไม่อยู่ใน roles โยน 403"""

    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "ไม่มีสิทธิ์ทำรายการนี้")
        return user

    return dep


admin = require_role("admin")
```

- `require_role` ไม่ได้ตรวจเอง มัน**สร้างตัวตรวจ**คืนมา (`dep`) — สร้างครั้งเดียวไว้ท้ายไฟล์ ทุก router `from app.auth import admin`
- `dep` พึ่ง `current_user` → FastAPI ตรวจ token ก่อน (401) แล้วค่อยตรวจบทบาท (403)
- `staff` เติมเฟส 3

## `app/models.py` — ตาราง `settings`

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

`CHECK id = 1` ทั้งตารางมีได้แถวเดียว · migration ต้อง**เติมมือ**หนึ่งบรรทัดท้าย `upgrade()` ให้มีแถวแรก:

```python
    op.execute("insert into settings (id) values (1)")
```

## `app/users/schemas.py` — เติมขาเข้า

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

- ชื่อผู้ใช้ อังกฤษ/ตัวเลข/`_.-` 3–50 ตัว · รหัส ≥ 6
- `UserUpdate` ทุกช่องไม่บังคับ ส่งเฉพาะที่จะแก้

## `app/users/service.py` — เติมสร้าง/แก้

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

- ชื่อซ้ำ → 409 ข้อความไทย (UNIQUE ในฐานกันอีกชั้น)
- ตั้งชื่อเงื่อนไขก่อน `if` (`is_self` `disabling` `demoting`) อ่านเป็นประโยคได้
- `model_dump(exclude_none=True, exclude={"password"})` เขียนเฉพาะช่องที่ส่งมา · รหัสใหม่ hash แยก

## `app/users/router.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.auth import admin
from app.db import get_db
from app.models import User
from app.users import service
from app.users.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/users", response_model=list[UserOut])
def list_users(db=Depends(get_db), _=Depends(admin)):
    """GET /api/users: admin ดูผู้ใช้ทั้งหมดเรียงตาม id"""
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(data: UserCreate, db=Depends(get_db), _=Depends(admin)):
    """POST /api/users: admin สร้างผู้ใช้ผ่าน service.create_user"""
    return service.create_user(db, data)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db=Depends(get_db), actor=Depends(admin)):
    """PATCH /api/users/{id}: admin แก้ชื่อ/role/สถานะ/รหัสผ่าน ผ่าน service.update_user"""
    return service.update_user(db, user_id, data, actor)
```

- ทุก endpoint บรรทัดเดียว: ตรวจสิทธิ์ → เรียก service → คืน schema
- `_=Depends(admin)` ตรวจแล้วทิ้งค่า · `actor=Depends(admin)` เก็บไว้ใช้ (service ต้องรู้ว่ากำลังแก้ตัวเองไหม)
- เรียกผ่าน `service.create_user` ชื่อเลยไม่ชนกับ endpoint `create_user`

## `app/settings/` — โดเมนใหม่

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

```python
from fastapi import APIRouter, Depends

from app.auth import admin, current_user
from app.db import get_db
from app.models import Setting
from app.settings import service
from app.settings.schemas import SettingsIn, SettingsOut

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings", response_model=SettingsOut)
def get_settings(db=Depends(get_db), _=Depends(current_user)):
    """GET /api/settings: ผู้ใช้ที่ล็อกอิน → คืนค่าตั้งอู่ (แถว id=1) จาก DB"""
    return db.get(Setting, 1)


@router.put("/settings", response_model=SettingsOut)
def update_settings(data: SettingsIn, db=Depends(get_db), _=Depends(admin)):
    """PUT /api/settings: admin ส่ง SettingsIn → service.update_settings → คืนค่าที่บันทึกแล้ว"""
    return service.update_settings(db, data)
```

- อ่านได้ทุกคน (หน้าอื่นใช้ชื่ออู่/VAT) · แก้ได้เฉพาะ admin (VAT ผิดทีเดียวกระทบบิลทั้งอู่)
- `SettingsOut` สืบจาก `SettingsIn` + `Out` — ช่องเดียวกัน แค่อ่านจาก ORM ได้

## เทสต์

```python
def test_admin_creates_user_and_duplicate_rejected(client, headers):
    body = {"username": "somchai", "password": "secret1", "full_name": "สมชาย", "role": "mechanic"}
    r = client.post("/api/users", json=body, headers=headers["admin"])
    assert r.status_code == 201 and "password_hash" not in r.json()
    assert client.post("/api/users", json=body, headers=headers["admin"]).status_code == 409


def test_short_password_rejected(client, headers):
    body = {"username": "somsri", "password": "123", "full_name": "สมศรี", "role": "employee"}
    assert client.post("/api/users", json=body, headers=headers["admin"]).status_code == 422


def test_login_with_created_user_and_password_change(client, headers):
    uid = client.post(
        "/api/users",
        json={"username": "noi", "password": "secret1", "full_name": "น้อย", "role": "employee"},
        headers=headers["admin"],
    ).json()["id"]
    client.patch(f"/api/users/{uid}", json={"password": "secret2"}, headers=headers["admin"])
    assert client.post("/api/auth/login", json={"username": "noi", "password": "secret1"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "noi", "password": "secret2"}).status_code == 200


def test_only_admin_manages_users(client, headers):
    for role in ("employee", "mechanic"):
        assert client.get("/api/users", headers=headers[role]).status_code == 403


def test_admin_cannot_deactivate_or_demote_self(client, headers, users):
    url = f"/api/users/{users['admin'].id}"
    assert client.patch(url, json={"is_active": False}, headers=headers["admin"]).status_code == 409
    assert client.patch(url, json={"role": "employee"}, headers=headers["admin"]).status_code == 409


def test_deactivated_user_token_stops_working(client, headers, users):
    client.patch(f"/api/users/{users['employee'].id}", json={"is_active": False}, headers=headers["admin"])
    assert client.get("/api/auth/me", headers=headers["employee"]).status_code == 401
```

```python
from app import models
from app.db import SessionLocal

SETTINGS = {"shop_name": "อู่ช่างเอ", "shop_address": "กรุงเทพฯ", "shop_tax_id": "0105555555555", "vat_rate": "7"}


def test_vat_rate_defaults_to_7():
    with SessionLocal() as s:
        assert s.get(models.Setting, 1).vat_rate == 7


def test_settings(client, headers):
    r = client.put("/api/settings", json={**SETTINGS, "vat_rate": "10"}, headers=headers["admin"])
    assert r.status_code == 200
    assert client.get("/api/settings", headers=headers["employee"]).json()["vat_rate"] == "10.00"
    assert client.put("/api/settings", json=SETTINGS, headers=headers["employee"]).status_code == 403
    assert client.put("/api/settings", json={**SETTINGS, "vat_rate": "-1"}, headers=headers["admin"]).status_code == 422
    assert client.get("/api/settings", headers=headers["mechanic"]).json()["shop_name"] == "อู่ช่างเอ"
```

---

# หน้าจอ

## `src/api.js` — เติม `plainNumber`

```js
// ตัดศูนย์ท้ายทิ้งไว้ใส่ช่องกรอก: "150.0000" → "150" (ต่างจาก formatMoney ที่ใส่ , และทศนิยมให้ ซึ่งพิมพ์ต่อไม่ได้)
export const plainNumber = (v) => (v === null || v === undefined || v === "" ? "" : String(Number(v)));
```

ใส่ตัวเลขลงช่องกรอก: `"7.00"` → `"7"` (ต่างจาก `formatMoney` ที่ใส่ `,` จนพิมพ์ต่อไม่ได้)

## `components/Field.jsx`

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

props ที่เหลือส่งต่อให้ `<input>` ทั้งหมด → ใช้กับ `{...register("ชื่อ")}` ได้ตรง ๆ (รวม `ref` ที่ react-hook-form ต้องการ)

## `components/Modal.jsx` — ป๊อปอัพ

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
      onClick={(e) => {
        // โดนตัว <dialog> เอง = คลิกฉากหลังนอกกล่อง (คลิกเนื้อหาข้างใน target จะเป็นลูกของมัน)
        if (e.target === ref.current) onClose();
      }}
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

- **render = เปิด · เลิก render = ปิด** ค่าในฟอร์มข้างในล้างเองทุกครั้ง ไม่ต้องมี state `open`
- `<dialog>` + `showModal()` ได้ฉากหลังมืด · Esc · กับดักโฟกัส ฟรีจากเบราว์เซอร์
- `onCancel` (Esc) กับคลิกฉากหลังเรียก `onClose` ให้คนเรียกตัดสินใจเอง
- มี `onSubmit` → ห่อทั้งกล่องด้วย `<form>` ปุ่มใน `footer` กด Enter ส่งได้

## `components/ListLayout.jsx` — เปลือกหน้ารายการ

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
          <Link to={action.to} className="btn btn-primary hidden md:inline-flex">
            <Icon name="plus" size={20} />
            {action.label}
          </Link>
        )}
      </div>
      {toolbar}
      {children}
      {action && (
        <Link
          to={action.to}
          aria-label={action.label}
          className="btn btn-primary btn-icon fixed right-4 bottom-6 z-20 size-14 rounded-2xl shadow-lg md:hidden"
        >
          <Icon name="plus" size={28} />
        </Link>
      )}
      {outlet}
    </section>
  );
}
```

- ปุ่มเพิ่ม: จอใหญ่อยู่หัว · มือถือเป็นปุ่มลอยมุมขวาล่าง
- `useOutlet({ close })` ส่ง `close()` ให้ป๊อปอัพที่เป็น route ลูก — ป๊อปอัพไม่ต้องรู้ว่าตัวเองอยู่ path ไหน

## `components/DataTable.jsx` — การ์ด/ตาราง

```jsx
import { Link, useNavigate } from "react-router-dom";

// แสดง items เป็นการ์ด (แคบ) หรือตาราง (กว้าง), คลิกแถวไปหน้า to(item)
export default function DataTable({ items, columns, card, to, empty = "ไม่มีข้อมูล" }) {
  const navigate = useNavigate();
  if (!items) return <p className="text-muted">กำลังโหลด…</p>;
  if (items.length === 0)
    return <p className="rounded-xl border border-dashed border-line py-10 text-center text-muted">{empty}</p>;

  // container query: แคบกว่า 48rem เป็นการ์ด กว้างกว่านั้นเป็นตาราง
  return (
    <div className="@container">
      <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-white @3xl:hidden">
        {items.map((item) => (
          <li key={item.id}>
            <Link to={to(item)} className="block px-4 py-3 transition-colors duration-150 hover:bg-surface">
              {card(item)}
            </Link>
          </li>
        ))}
      </ul>
      <div className="hidden overflow-x-auto rounded-xl border border-line bg-white @3xl:block">
        <table className="table">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.label} className={c.align === "right" ? "text-right" : ""}>
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr
                key={item.id}
                onClick={(e) => {
                  // คลิกโดน <Link> ในแถว ปล่อยให้ Link ทำเอง (ไม่งั้นไปหน้าเดิมซ้ำ และ Ctrl+คลิกแท็บเดิมก็เปลี่ยนหน้า)
                  if (!e.target.closest("a")) navigate(to(item));
                }}
              >
                {columns.map((c, i) => (
                  <td key={c.label} className={c.align === "right" ? "num text-right" : ""}>
                    {i === 0 ? (
                      <Link to={to(item)} className="font-semibold hover:underline">
                        {c.render(item)}
                      </Link>
                    ) : (
                      c.render(item)
                    )}
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

- วาดสองแบบจากข้อมูลชุดเดียว แล้วให้ CSS ซ่อนแบบที่ไม่ใช้
- `@container` / `@3xl:` ดูความกว้าง**กล่อง** ไม่ใช่จอ — ใส่ในป๊อปอัพหรือคอลัมน์แคบก็เปลี่ยนเป็นการ์ดเองถูกต้อง
- คอลัมน์แรกเป็น `<Link>` (กด Tab ถึง · คลิกขวาเปิดแท็บใหม่ได้) · `<tr>` ข้ามการคลิกที่โดนลิงก์ ไม่งั้นเปลี่ยนหน้าซ้ำสองรอบ
- `items` ยังไม่มา → "กำลังโหลด…" · ว่าง → ข้อความ `empty`

## `components/StatusBadge.jsx` (ทั้งไฟล์ ณ จบเฟส 3)

```jsx
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
```

คำและสีของสถานะอยู่ที่เดียว · `productStatus` กับ `low` `inactive` เติมเฟส 3

## `components/SettingsTabs.jsx`

```jsx
import { NavLink } from "react-router-dom";

// แท็บสลับ ตั้งค่าอู่ / ผู้ใช้
export default function SettingsTabs() {
  return (
    <nav aria-label="หมวดตั้งค่า" className="tabs">
      <NavLink to="/settings" end className="tab">
        ตั้งค่าอู่
      </NavLink>
      <NavLink to="/settings/users" className="tab">
        ผู้ใช้
      </NavLink>
    </nav>
  );
}
```

`NavLink` ใส่ `aria-current="page"` ให้เองเมื่อตรงหน้าปัจจุบัน → `.tab` ขีดเส้นใต้ (`end` = ต้องตรงเป๊ะ ไม่นับ `/settings/users`)

## `pages/SettingsPage.jsx`

```jsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { api, plainNumber } from "../api";
import Field from "../components/Field";
import Icon from "../components/Icon";
import SettingsTabs from "../components/SettingsTabs";

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
      <section className="card space-y-4">
        <h2 className="font-semibold">ข้อมูลบนหัวเอกสาร</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="ชื่ออู่" {...register("shop_name")} />
          <Field label="เลขประจำตัวผู้เสียภาษี" {...register("shop_tax_id")} />
          <Field label="ที่อยู่" {...register("shop_address")} />
        </div>
      </section>
      <section className="card space-y-4">
        <h2 className="font-semibold">ค่าระบบ</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="อัตรา VAT (%)" type="number" inputMode="decimal" step="any" {...register("vat_rate")} />
        </div>
      </section>
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

- แยกสองชิ้น: `SettingsPage` โหลด · `SettingsForm` ฟอร์ม — เพราะ `useForm` จำ `defaultValues` ครั้งแรกครั้งเดียว ต้องรอข้อมูลมาก่อนค่อยสร้างฟอร์ม
- บันทึกแล้ว `setQueryData` ใส่ค่าที่ตอบกลับลง cache ตรง ๆ ไม่ยิง GET ซ้ำ

## `pages/UserListPage.jsx` — แบบของหน้ารายการทุกหน้า

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
export default function UserListPage() {
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

```
useQuery([...])   ดึงรายการ
<ListLayout>      หัว + ปุ่มเพิ่ม + ที่ให้ป๊อปอัพมาเปิด
  <DataTable>     card={...} columns={...} บอกว่าหน้านี้วาดข้อมูลยังไง
```

`truncate` + `min-w-0` = ชื่อยาวตัดเป็น … แทนดันป้ายตกขอบ

## `pages/UserFormPage.jsx` — ป๊อปอัพเพิ่ม/แก้ผู้ใช้

```jsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useOutletContext, useParams } from "react-router-dom";
import { api } from "../api";
import { ROLE_NAME, useAuth } from "../auth";
import Field from "../components/Field";
import Modal from "../components/Modal";

const EMPTY = { username: "", full_name: "", role: "employee", password: "" };

// popup ผู้ใช้ /settings/users/new หรือ /:id: หา user จาก cache ["users"] ชุดเดียวกับ UserListPage
// (มีของแล้ววาดทันที แล้ว TanStack Query ดึงใหม่เบื้องหลังหนึ่งครั้ง) แล้วส่งให้ UserForm
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
  const { user: me, setUser } = useAuth();
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
    onSuccess: (saved) => {
      if (saved.id === me.id) setUser(saved); // แก้บัญชีตัวเอง → ชื่อในแถบข้างเปลี่ยนตาม
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

- `UserFormPage` หาว่าจะแก้ใคร (id จาก URL + cache) · `UserForm` คือฟอร์ม
- `key={id ?? "new"}` เปลี่ยนคน = React สร้างฟอร์มใหม่ (ไม่งั้นเปิดคนที่ 8 แต่ยังเห็นค่าคนที่ 5)
- `String(u.id) === id` เพราะค่าจาก URL เป็น string เสมอ
- สอง mutation: บันทึก (ปิดป๊อปอัพ) · ปิด/เปิดใช้งาน (อยู่ต่อ) ใช้ `busy` / `error` ร่วมกัน
- แก้บัญชีตัวเอง → `setUser(saved)` เพราะชื่อในแถบข้างมาจาก `auth.jsx` ไม่ใช่ cache `["users"]`
- ช่องรหัสผ่านตอนแก้: เว้นว่าง = ไม่เปลี่ยน (ส่ง `null`)

route ของหน้านี้อยู่ใน `main.jsx` (ดูเฟส 1): `/settings` และ `/settings/users` (+ ลูก `new` `:id`) ครอบ `Guard roles={ADMIN}`

---

## เช็คว่าเสร็จ

- pytest เขียว · `npm run build` ผ่าน
- admin: สร้างช่างได้ · ชื่อซ้ำขึ้นข้อความ · ปิดบัญชีตัวเองไม่ได้ · แก้ชื่อตัวเองแล้วแถบข้างเปลี่ยน
- ล็อกอินเป็นช่าง: ไม่มีเมนูตั้งค่า · พิมพ์ `/settings` ตรง ๆ ก็เด้งออก · ยิง `PUT /api/settings` ได้ 403
- เปิด `/settings/users/5` ตรง ๆ แล้ว F5 → ป๊อปอัพยังเปิดอยู่
