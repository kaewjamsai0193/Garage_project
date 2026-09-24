# แผนที่ระบบ — ข้อมูลเดินจากไหนไปไหน

อ่านไฟล์นี้ก่อนเสมอ แล้วเปิดโค้ดจริงตามชื่อไฟล์/ฟังก์ชันที่ชี้

## 1. ภาพรวม

```
มือถือ / คอม
   │ http://<เครื่องอู่>:5173
   ▼
web  (React + Vite)   ── /api/* ──►  api  (FastAPI)  ──►  db  (PostgreSQL)
เปิดให้ทั้งวงแลน                     127.0.0.1:8000        ใน docker เท่านั้น
                                     (ไว้เปิด /docs)
```

- มือถือเข้าผ่าน 5173 อย่างเดียว Vite ส่ง `/api` ต่อให้ api ภายใน docker เอง
- ฐานข้อมูลไม่เปิดออกนอก docker · เข้าเองใช้ `docker compose exec db psql -U garage -d garage`

## 2. หนึ่งคำขอเดินยังไง

```
หน้าจอ  useQuery (อ่าน) / useMutation (บันทึก)
  → frontend/src/api.js          แนบ token · error → ข้อความไทย · 401 → ลบ token ไปหน้า login
  → Vite proxy /api → api:8000
  → <โดเมน>/router.py            URL + ตรวจสิทธิ์ · อ่านข้อมูลธรรมดาได้ แต่ไม่เขียน
  → <โดเมน>/service.py           กฎธุรกิจ · ล็อก · เขียนฐาน (ที่เดียวที่ commit)
  → models.py → PostgreSQL

ขากลับ: ORM object → schema (ตัดช่องที่ไม่ให้เห็น: password_hash, ต้นทุน) → JSON → cache → หน้าจอ
```

## 3. ตอนเปิดระบบ (`docker compose up`)

```
db   สร้างฐาน garage_test (เฉพาะ volume ใหม่) → healthcheck ผ่าน
api  alembic upgrade head                      ตารางตามโค้ดเสมอ
     import auth.py                            JWT_SECRET ว่าง/ค่าตัวอย่าง → ไม่ยอมเริ่ม
     main.py:lifespan → users/service.py:ensure_admin()
                                               ยังไม่มี admin → สร้างจาก ADMIN_* ใน .env
                                               (ว่าง หรือรหัส < 6 ตัว → ไม่ยอมเริ่ม)
web  npm install → vite dev
```

## 4. ล็อกอิน

```
pages/LoginPage.jsx      handleSubmit → signIn.mutate(form)
  → auth.jsx:login       api("/auth/login", POST)
  → users/auth_router.py:login
       หา user ตามชื่อ → auth.py:verify_password → auth.py:create_token (user_id + exp)
       ชื่อผิด / รหัสผิด / บัญชีปิด → 401 ข้อความเดียวกัน
  ← { access_token, user }
  → setToken (localStorage) + setUser → LoginPage เจอ user → <Navigate to="/">
```

## 5. เปิดเว็บใหม่ / กด F5

```
auth.jsx (useEffect ครั้งแรก)
  ไม่มี token → user = null
  มี token    → GET /auth/me → auth.py:current_user
                 ถอด token → db.get(User) → ต้อง is_active
                 ผ่าน → setUser(user) · ไม่ผ่าน 401 → api.js ลบ token → /login
```

| `user` | ความหมาย | `Guard` ใน main.jsx |
|---|---|---|
| `undefined` | กำลังเช็ค `/auth/me` | ไม่วาดอะไร (กันหน้ากระพริบ) |
| `null` | ไม่ได้ล็อกอิน | ไป `/login` |
| object | ล็อกอินแล้ว | วาดหน้า · บทบาทไม่อยู่ใน `roles` → ไป `/` |

## 6. อ่านข้อมูล — `useQuery`

```
useQuery({ queryKey: ["products", id, "lots"] })
  → api.js queryFn: "/" + queryKey.join("/")  →  GET /api/products/{id}/lots
  → เก็บใน cache ใต้กุญแจนั้น
```

- กุญแจ = path ของ API แยกเป็นท่อน · ท่อนแรกคือ "กลุ่มข้อมูล"
- หน้าอื่นขอกุญแจเดียวกัน → ได้ของจาก cache ทันที แล้วดึงใหม่เบื้องหลังหนึ่งครั้ง

## 7. บันทึก — `useMutation`

```
handleSubmit → save.mutate(form)
  → api(path, { method, body }) → router → service → commit
  → onSuccess: invalidateQueries({ queryKey: ["กลุ่ม"] })
       → ทุก useQuery ที่กุญแจขึ้นต้นด้วยกลุ่มนั้นดึงใหม่เอง
```

| บันทึกอะไร | หลังสำเร็จ |
|---|---|
| สินค้า · ปรับสต็อก | invalidate `["products"]` → รายการ + ตัวเดียว + Lot + สมุดสต็อก |
| ผู้ใช้ | invalidate `["users"]` · ถ้าแก้บัญชีตัวเอง `setUser` ด้วย (ชื่อในแถบข้าง) |
| ค่าตั้งอู่ | `setQueryData(["settings"], ค่าที่ตอบกลับ)` ไม่ต้อง GET ซ้ำ |
| ออกจากระบบ | `queryClient.clear()` ล้าง cache ทั้งหมด (กันคนถัดไปเห็นต้นทุนค้าง) |

## 8. ตรวจสิทธิ์

```
router:  Depends(current_user)           ไม่มี/ผิด token/บัญชีปิด → 401
         Depends(admin) / Depends(staff)  บทบาทไม่ตรง → 403      (ประกาศไว้ใน auth.py)
ต้นทุน:  schemas.py:serialize_for_role  admin ได้ XxxAdminOut · คนอื่นได้ XxxOut (ไม่มีช่องต้นทุน)
```

หน้าจอซ่อนเมนู/ปุ่มตามบทบาท = ความสะดวกเท่านั้น ด่านจริงอยู่ที่ backend

| ทำอะไร | admin | employee | mechanic |
|---|:---:|:---:|:---:|
| ดูสินค้า · Lot · สมุดสต็อก · ค่าตั้ง | ✅ | ✅ | ✅ |
| เห็นต้นทุน | ✅ | – | – |
| เพิ่ม/แก้สินค้า · ปรับลด/เพิ่มใน Lot | ✅ | ✅ | – |
| สต็อกตั้งต้น | ✅ | – | – |
| จัดการผู้ใช้ · แก้ค่าตั้ง | ✅ | – | – |

## 9. แผนที่ไฟล์ (จบเฟส 3)

```
backend/app/
  main.py      สร้างแอป · รวม router · IntegrityError → 409 · lifespan → ensure_admin
  db.py        engine · get_db · get_or_404 · lock_shop
  auth.py      hash/verify รหัส · create_token · current_user · require_role · admin · staff
  models.py    ทุกตาราง: users · settings · products · stock_lots · stock_movements
  money.py     round_money · format_qty
  schemas.py   In · Out · serialize_for_role
  users/       auth_router.py (/auth/login /auth/me) · router.py (/users) · service.py · schemas.py
  settings/    router.py (/settings) · service.py · schemas.py
  stock/       router.py (/products /stock) · service.py · schemas.py

frontend/src/
  main.jsx     route ทั้งหมด + Guard
  api.js       api() · queryClient · formatMoney/formatQty/formatDate/plainNumber
  auth.jsx     AuthProvider · useAuth · ROLE_NAME
  components/  AppLayout ListLayout DetailLayout DataTable Modal ReasonDialog ProductModal
               Field SearchBar SettingsTabs StatusBadge Icon
  pages/       LoginPage SettingsPage UserListPage UserFormPage
               ProductListPage ProductFormPage ProductDetailPage
```

เฟส 4 จะเพิ่ม: `purchasing/` · `textutil.py` · `ProductSearch` · `PurchaseOrder*Page` · `GoodsReceipt*Page`

## ไล่โค้ดเวลาอ่าน

เริ่มจากสิ่งที่คนกดบนจอ แล้วตามลูกศร:
`หน้าจอ → queryKey / mutationFn → api.js → URL → router.py → service.py → models.py`
