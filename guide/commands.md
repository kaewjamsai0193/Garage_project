# คำสั่งทั้งหมด

เปิด Docker Desktop ทิ้งไว้ก่อนเสมอ · รันจากโฟลเดอร์โปรเจ็ค (ที่มี `docker-compose.yml`)

## รันระบบ
```
docker compose up --build        # ครั้งแรก หรือหลังแก้ requirements.txt / Dockerfile
docker compose up                # ครั้งต่อไป
docker compose up -d             # รันเบื้องหลัง
docker compose down              # หยุด
docker compose down -v           # หยุด + ลบข้อมูลในฐานทิ้งทั้งหมด (ระวัง)
docker compose logs -f api       # ดู log ตอน API พัง
docker compose ps                # เช็คว่าตัวไหนขึ้นบ้าง
```
เว็บ http://localhost:5173 · API http://localhost:8000 · เอกสาร API http://localhost:8000/docs

## เทสต์
```
docker compose run --rm api pytest                       # ทั้งชุด
docker compose run --rm api pytest -q                    # สั้น ๆ
docker compose run --rm api pytest tests/test_stock.py   # ไฟล์เดียว
docker compose run --rm api pytest -k fifo               # เฉพาะเทสต์ที่ชื่อมี fifo
docker compose run --rm api pytest -x -vv                # หยุดที่ตัวแรกที่พัง + รายละเอียด
```

## จัดรูปแบบโค้ด + ตรวจ (ก่อน commit ทุกครั้ง)
```
docker compose run --rm api ruff check --fix .   # backend: หาจุดผิด + แก้ที่แก้เองได้ (import ไม่ใช้ · เรียง import)
docker compose run --rm api ruff format .        # backend: จัดรูปแบบ
docker compose exec -T web npm run format        # หน้าจอ: Prettier จัดรูปแบบ src/
```
ค่าตั้ง: `backend/ruff.toml` · `frontend/.prettierrc` (บรรทัดยาวสุด 120 ทั้งคู่)

## ฐานข้อมูล (Alembic)
```
docker compose run --rm api alembic revision --autogenerate -m "add stock tables"
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic downgrade -1
docker compose run --rm api alembic current
docker compose run --rm api alembic history
```
**ไฟล์ที่ autogenerate ออกมาต้องเปิดอ่านทุกครั้ง** มันเดา partial index กับ CHECK ไม่เก่ง ต้องแก้มือ

## เข้าฐานข้อมูลตรง ๆ
```
docker compose exec db psql -U garage -d garage
```
ในนั้น: `\dt` ดูตาราง · `\d products` ดูโครงตาราง · `\q` ออก

## หน้าจอ
```
docker compose exec -T web npm run build     # ต้องผ่านก่อน commit ทุกครั้ง
docker compose restart web                   # เวลา hot reload ค้าง
docker compose run --rm web npm install ชื่อแพ็กเกจ
```

## ข้อมูลเดโม

ยังไม่มีในเฟส 0–4 (มาเฟส 9) ตอนนี้กดสร้างข้อมูลเองผ่านหน้าจอ

## git
```
git init                         # ครั้งเดียวตอนเริ่ม
git add -A
git commit -m "feat: ..."
git log --oneline
```

## เวลาติด
| อาการ | ทำอะไร |
|---|---|
| `port is already allocated` | `docker compose down` ก่อน หรือเปลี่ยนเลข port ซ้ายมือใน compose |
| api ขึ้นแล้วดับทันที | `docker compose logs api` — ส่วนใหญ่คือ migration พัง |
| แก้โค้ดแล้วหน้าเว็บไม่เปลี่ยน | เช็ค `usePolling: true` ใน vite.config.js แล้ว `docker compose restart web` |
| แก้ไฟล์ migration แล้วไม่มีผล (เช่น ตาราง settings ว่าง) | แก้หลัง `upgrade` ไปแล้ว alembic ไม่รันซ้ำ → `alembic downgrade -1` แล้ว `upgrade head` (ข้อมูลตารางในไฟล์นั้นหายนะ) |
| `Can't locate revision ...` ตอน upgrade | ฐานยังจำ migration ของโค้ดชุดเก่า → `docker compose down -v` แล้ว `up` ใหม่ (ข้อมูลในฐานหายหมด) |
| รับของแล้วได้ "ข้อมูลขัดกับกฎของระบบ" (เฟส 4) | ลืมแก้ CHECK ด้วยมือใน migration เฟส 4 → ดูหัวข้อ migration ใน [04-purchasing.md](04-purchasing.md) |
| เทสต์พังเพราะตารางไม่ตรง | `alembic upgrade head` ยังไม่ได้รัน หรือ migration ยังไม่ถูกสร้าง |
| เทสต์เขียนทับข้อมูลจริง | เช็คว่า conftest.py ตั้ง `DATABASE_URL = TEST_DATABASE_URL` **ก่อน** import app |
| `docker compose build` พัง `Invalid requirement: '...>=0.2ruff>=0.6'` | บรรทัดท้าย `requirements.txt` ไม่มีขึ้นบรรทัดใหม่ แล้วต่อท้ายไฟล์ไปติดกัน → แยกเป็นสองบรรทัด |
| `ruff check` เตือน `B008` ที่ `Depends(...)` | ลืม `ruff.toml` (ปิด B008 ไว้) — ดูเฟส 0 |
| หน้าจอข้อมูลไม่อัปเดตหลังบันทึก | `invalidateQueries` ใช้กุญแจไม่ตรง — ท่อนแรกต้องเหมือน `useQuery` ที่หน้านั้นใช้ (`["products"]` จับ `["products", id, "lots"]` ได้ แต่กลับกันไม่ได้) |
| ฟอร์ม `register` แล้วค่าไม่เข้า / ได้ `undefined` | ลืม `{...register("ชื่อ")}` หรือชื่อไม่ตรงกับช่องใน `defaultValues` · ถ้าช่องอยู่ในคอมโพเนนต์ของเราเอง ต้องส่ง props (รวม `ref`) ต่อถึง `<input>` แบบ `Field` |
| ข้อความ error ขึ้นเป็น `[object Object]` | `useQuery`/`useMutation` ให้ `error` เป็น object ต้องเขียน `error.message` |
