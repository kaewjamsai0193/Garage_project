# ระบบจัดการอู่ซ่อมรถ

ระบบจัดการอู่ซ่อมรถ: ผู้ใช้และสิทธิ์ · ค่าตั้งอู่ · สินค้าและสต็อกแบบแยก Lot ต้นทุน

| ส่วน | ใช้อะไร |
|---|---|
| backend | FastAPI + SQLAlchemy 2 + Alembic (Python 3.12) |
| ฐานข้อมูล | PostgreSQL 16 |
| หน้าจอ | React 19 + Vite + Tailwind 4 · TanStack Query (ข้อมูล) · react-hook-form (ฟอร์ม) |
| รันทั้งหมด | Docker Compose (db + api + web) |

## รันบนเครื่องใหม่

**ต้องมีก่อน:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (เปิดค้างไว้) และ Git
ไม่ต้องลง Python หรือ Node ลงเครื่อง ทุกอย่างรันในคอนเทนเนอร์

```bash
git clone https://github.com/kaewjamsai0193/Garage_project.git
cd Garage_project
cp .env.example .env
```

**แก้ไฟล์ `.env` ก่อนรัน** — สามค่านี้ต้องกรอกเอง

```
JWT_SECRET=<ข้อความยาว ๆ สุ่ม ๆ อะไรก็ได้>
ADMIN_USERNAME=<ชื่อผู้ใช้ของเจ้าของอู่>
ADMIN_PASSWORD=<รหัสผ่านอย่างน้อย 6 ตัว>
```

`.env` ไม่เข้า git (มีความลับอยู่ข้างใน) ส่วน `.env.example` เป็นแม่แบบให้รู้ว่าต้องตั้งอะไรบ้าง

```bash
docker compose up --build        # ครั้งแรกใช้เวลาสักพัก (โหลด image + ลง dependency)
```

ขึ้นครบแล้วเปิด:

| ที่อยู่ | คืออะไร |
|---|---|
| http://localhost:5173 | หน้าเว็บ |
| http://localhost:8000/docs | เอกสาร API ที่ FastAPI สร้างให้ ลองยิงได้จากหน้านี้เลย |
| http://localhost:8000/api/health | เช็คว่า API ยังทำงาน ควรได้ `{"ok":true}` |

**เข้าระบบครั้งแรก** ด้วย `ADMIN_USERNAME` / `ADMIN_PASSWORD` ที่ตั้งไว้ใน `.env`
ตอนเซิร์ฟเวอร์เริ่มทำงาน ถ้ายังไม่มีบัญชี admin ในฐาน ระบบจะสร้างบัญชีนี้ให้อัตโนมัติ
จากนั้นเพิ่มบัญชีพนักงานกับช่างได้ที่ ตั้งค่า → ผู้ใช้

ฐานข้อมูล ตาราง และค่าตั้งเริ่มต้นถูกสร้างให้เองตอนเริ่ม (`alembic upgrade head` อยู่ในคำสั่งเริ่ม api)

## คำสั่งที่ใช้บ่อย

```bash
docker compose up -d             # รันเบื้องหลัง
docker compose down              # หยุด (ข้อมูลในฐานยังอยู่)
docker compose down -v           # หยุด + ลบข้อมูลในฐานทิ้งทั้งหมด
docker compose logs -f api       # ดู log ตอน API พัง
docker compose ps                # เช็คว่าตัวไหนขึ้นบ้าง
```

**เทสต์และคุณภาพโค้ด**

```bash
docker compose exec api python -m pytest -q      # เทสต์ backend (ใช้ฐาน garage_test แยกจากของจริง)
docker compose exec api ruff check --fix .       # lint backend + แก้ที่แก้เองได้
docker compose exec api ruff format .            # จัดรูปแบบ backend
docker compose exec web npm run format           # จัดรูปแบบหน้าจอ (Prettier)
docker compose exec web npm run build            # ต้องผ่านก่อน commit
```

**ฐานข้อมูล**

```bash
docker compose exec api alembic revision --autogenerate -m "ข้อความ"   # สร้าง migration (เปิดอ่านไฟล์ที่ได้ทุกครั้ง)
docker compose exec api alembic upgrade head                           # อัปเดตโครงฐาน
docker compose exec db psql -U garage -d garage                        # เข้าฐานตรง ๆ (\dt ดูตาราง, \q ออก)
```

## โครงไฟล์

```
backend/app/
  main.py  db.py  auth.py  models.py  money.py  schemas.py   ของกลางที่ทุกโดเมนใช้
  users/  settings/  stock/                                  หนึ่งโดเมนหนึ่งโฟลเดอร์
    router.py    URL + ตรวจสิทธิ์ → เรียก service
    service.py   กฎธุรกิจ + เขียนข้อมูลลงฐาน
    schemas.py   รูปแบบข้อมูลเข้า-ออก
frontend/src/
  api.js       ที่เดียวที่คุยกับ backend + ตัวจัดรูปแบบตัวเลข/วันที่
  auth.jsx     จำว่าใครล็อกอินอยู่
  components/  ของใช้ร่วมทุกหน้า (ป๊อปอัพ ตาราง ป้ายสถานะ ฯลฯ)
  pages/       หน้าจอแต่ละหน้า
```

**ทางเดินของหนึ่งคำขอ:** หน้าจอ → `api.js` → `<โดเมน>/router.py` → `<โดเมน>/service.py` → `models.py` → PostgreSQL

## เวลาติดปัญหา

| อาการ | ทำอะไร |
|---|---|
| `port is already allocated` | มีอย่างอื่นใช้ port อยู่ → `docker compose down` ก่อน หรือเปลี่ยนเลข port ซ้ายมือใน `docker-compose.yml` |
| api ขึ้นแล้วดับทันที | `docker compose logs api` ส่วนใหญ่คือ migration พัง หรือ `.env` ยังไม่ได้ตั้ง |
| ล็อกอินไม่ได้ตั้งแต่ครั้งแรก | ตอนรันครั้งแรก `.env` ยังไม่มี `ADMIN_USERNAME`/`ADMIN_PASSWORD` → ตั้งค่าแล้ว `docker compose down -v` เพื่อเริ่มฐานใหม่ |
| แก้โค้ดแล้วหน้าเว็บไม่เปลี่ยน | `docker compose restart web` |
| ลง package ใหม่แล้วหน้าเว็บขาว | `docker compose exec web npm install` แล้ว `docker compose restart web` (node_modules อยู่ในคอนเทนเนอร์) |
| เทสต์พังเพราะตารางไม่ตรง | `docker compose exec api alembic upgrade head` |
