# แผนที่ระบบ

อ่านคู่กับ [เฟส 1](01-base-login.md) — เน้นว่า **ไฟล์ไหนเรียกฟังก์ชันไหน และข้อมูลไหลไปทางใด**

## 1. ภาพรวม: บ้านหลังเดียว 3 ห้อง

```
┌──────────────────────── docker compose ────────────────────────┐
│                                                                │
│   web (หน้าจอ)          api (สมอง)            db (โกดังข้อมูล)   │
│   React + Vite    ───►  FastAPI (Python) ───► PostgreSQL        │
│   localhost:5173        localhost:8000        localhost:5432    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

จำสั้น ๆ: **หน้าจอ → `api.js` → Vite proxy → `<โดเมน>/router.py` → `<โดเมน>/service.py` → `models.py` → PostgreSQL**

## 2. ตอนสั่ง `docker compose up`

```
db   : Postgres เริ่ม → (volume ใหม่เท่านั้น) รัน db/init/01-test-db.sql สร้างฐาน garage_test
          │ healthcheck ผ่าน
          ▼
api  : alembic upgrade head
          alembic/env.py ── import app.models ──► ลงทะเบียนทุกตารางใน Base.metadata
          alembic/versions/*.py ──► สร้าง/แก้ตารางให้ตรงกับโค้ด
       uvicorn app.main:app
          main.py:lifespan() ──► users/service.py:ensure_admin() ──► auth.py:hash_password()
                                  (สร้าง admin จาก .env ถ้ายังไม่มีผู้ใช้เลย)
web  : npm install → vite dev server (proxy /api → http://api:8000)
```

## 3. ตอนกดเข้าสู่ระบบ

```text
handleSubmit → signIn.mutate(form)            frontend/src/pages/LoginPage.jsx   (react-hook-form รวบค่า → useMutation)
  → useAuth().login()                         frontend/src/auth.jsx
    → api("/auth/login", POST)                frontend/src/api.js
      → POST /api/auth/login                  Vite proxy → container api
        → login()                             backend/app/users/auth_router.py
          → LoginIn                           backend/app/users/schemas.py   (ตรวจรูปแบบ + ตัดช่องว่าง)
          → get_db()                          backend/app/db.py
          → select(User)                      backend/app/models.py
          → verify_password()                 backend/app/auth.py
          → create_token()                    backend/app/auth.py
          → LoginOut                          backend/app/users/schemas.py   (UserOut ไม่มี password_hash)
    → setToken() + setUser()                  frontend/src/auth.jsx
  → <Navigate to="/">                         frontend/src/pages/LoginPage.jsx
```

## 4. ตอนกด F5 หลังเคยล็อกอิน

token ยังอยู่ใน `localStorage` แต่ frontend **ยังไม่เชื่อทันที** ต้องถาม backend ก่อน

```text
AuthProvider useEffect                        frontend/src/auth.jsx     user = undefined (Guard ยังไม่วาด)
  → api("/auth/me")                           frontend/src/api.js
    → me()                                    backend/app/users/auth_router.py
      → current_user()                        backend/app/auth.py
        → jwt.decode() → db.get(User)         token ยังไม่หมดอายุ และบัญชียัง active?
  ผ่าน  → setUser(object)  → Guard วาด AppLayout
  ไม่ผ่าน (401) → api.js ลบ token + ไป /login
```

| ค่า `user` | ความหมาย | `Guard` ทำอะไร |
|---|---|---|
| `undefined` | กำลังตรวจ `/auth/me` | ยังไม่วาด ป้องกันหน้ากระพริบ |
| `null` | ไม่ได้ล็อกอิน | ไป `/login` |
| object | ล็อกอินแล้ว | แสดง `AppLayout` และหน้าข้างใน |

## 5. ตอนเปิดหน้าที่มีข้อมูล และตอนกดบันทึก (ตั้งแต่เฟส 2)

**เปิดหน้า** — ตัวอย่างหน้ารายชื่อผู้ใช้

```text
useQuery({ queryKey: ["users"] })             frontend/src/pages/UsersPage.jsx
  → queryClient มีของใต้ ["users"] ไหม        frontend/src/api.js
     มี   → คืนของเดิมทันที (แล้วอาจดึงใหม่เบื้องหลัง)
     ไม่มี → queryFn: api("/" + ["users"].join("/"))  → GET /api/users
  → { data, error }                           หน้าจอวาดตาม data
```

**กดบันทึก** — ตัวอย่างแก้ผู้ใช้

```text
handleSubmit → save.mutate(form)              frontend/src/pages/UserFormPage.jsx
  → mutationFn: api("/users/5", PATCH)        frontend/src/api.js → backend
  → onSuccess:
      invalidateQueries({ queryKey: ["users"] })   ข้อมูลใต้ ["users"] เก่าแล้ว
        → ทุกหน้าที่ใช้ ["users"] อยู่ ดึงใหม่เอง (UsersPage + UserFormPage)
      close()                                 ปิดป๊อปอัพ
```

**กฎของ `queryKey`** — ท่อนแรกคือกลุ่มข้อมูล ที่เหลือคือ path ต่อ

| queryKey | ยิง | invalidate ด้วย `["products"]` โดนไหม |
|---|---|---|
| `["products"]` | `GET /products` | โดน |
| `["products", "5"]` | `GET /products/5` | โดน |
| `["products", "5", "lots"]` | `GET /products/5/lots` | โดน |
| `["users"]` | `GET /users` | ไม่โดน |

## 6. การตรวจสิทธิ์ของ API (ตั้งแต่เฟส 2)

การซ่อนเมนูใน `AppLayout.jsx` ช่วยแค่เรื่องหน้าจอ ความปลอดภัยจริงอยู่ที่ backend ตัวอย่าง `PATCH /api/users/{id}`:

```text
users/router.py:update_user()
  → Depends(admin)                  admin = require_role("admin")        auth.py
    → current_user()                ไม่มี/ผิด token → 401
    → user.role ไม่อยู่ใน roles     → 403
  → users/service.py:update_user()  กฎธุรกิจ + เขียนข้อมูล
    → db.py:get_or_404()            ไม่พบ → 404
    → db.commit()
  → users/schemas.py:UserOut        ส่งกลับเฉพาะฟิลด์ที่อนุญาต
```

## 7. แผนที่ไฟล์ ณ จบเฟส 4

```
backend/app/
  main.py  db.py  auth.py  models.py  money.py  textutil.py  schemas.py
  users/       auth_router.py  router.py  schemas.py  service.py      /api/auth  /api/users
  settings/    router.py  schemas.py  service.py                      /api/settings
  stock/       router.py  schemas.py  service.py                      /api/products  /api/stock
  purchasing/  router.py  schemas.py  service.py                      /api/purchase-orders  /api/goods-receipts
                              └─ import app.stock.service.products_by_id

frontend/src/
  main.jsx  api.js  auth.jsx  index.css
  components/  Icon AppLayout Field Modal ListLayout DataTable StatusBadge SettingsTabs
               SearchBar DetailLayout ReasonDialog ProductSearch
  pages/       LoginPage SettingsPage UsersPage UserFormPage ProductListPage ProductFormPage ProductDetailPage
               PurchaseOrdersPage PurchaseOrderNewPage PurchaseOrderPage GoodsReceiptsPage GoodsReceiptNewPage GoodsReceiptPage PrintPOPage
```

## วิธีไล่โค้ดเวลาอ่านต่อ

เริ่มจากสิ่งที่ผู้ใช้ทำ แล้วอ่านตามลูกศร:

```text
หน้าจอ → useQuery (queryKey) หรือ useMutation (mutationFn) → api.js → URL → <โดเมน>/router.py → Depends/schema
       → <โดเมน>/service.py (ถ้าเขียนข้อมูล) → models.py → db.py → PostgreSQL
```

ขากลับอ่านกลับทาง:

```text
PostgreSQL → ORM object → response_model/schema → JSON → api.js → queryClient (cache) → หน้าจอ
```

หลังบันทึก: `onSuccess` ของ `useMutation` → `invalidateQueries` → `useQuery` ที่ใช้กุญแจนั้นดึงใหม่ → หน้าจออัปเดตเอง
