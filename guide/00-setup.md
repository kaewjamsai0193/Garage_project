# เฟส 0 — ติดตั้ง + โครงเปล่า

**จบเฟสนี้:** `docker compose up --build` ขึ้นครบ 3 ตัว · http://localhost:8000/api/health ได้ `{"ok":true}` · http://localhost:5173 เปิดหน้าเว็บได้

**ในเครื่องมีแค่** Docker Desktop + Git — Python กับ Node รันในคอนเทนเนอร์ทั้งหมด

> โค้ดในไฟล์นี้คือของจริงใน repo ตอนจบเฟส 3 · ถ้าไฟล์จริงเปลี่ยน ให้ยึดไฟล์จริง

## ขึ้นระบบแล้วเกิดอะไร

```
cp .env.example .env   → กรอก JWT_SECRET · ADMIN_USERNAME · ADMIN_PASSWORD
docker compose up --build
 ├─ db   postgres:16 → (volume ใหม่เท่านั้น) db/init/01-test-db.sql สร้างฐาน garage_test → healthcheck
 ├─ api  รอ db healthy → alembic upgrade head → uvicorn --reload
 └─ web  npm install → vite dev --host · /api/* ส่งต่อไป http://api:8000
```

## กฎหลัก

- **ทุกอย่างรันใน docker** ติดตั้งแพ็กเกจเพิ่มก็สั่งผ่านคอนเทนเนอร์
- **เปิด port เท่าที่ใช้** — db ไม่เปิดเลย · api เปิดเฉพาะเครื่องนี้ · web เปิดทั้งวงแลนให้มือถือ
- **migration รันเองทุกครั้งที่ api เริ่ม** ฐานตรงกับโค้ดเสมอ
- **api รอ db healthcheck** ไม่งั้น alembic พังทุกครั้งที่เปิดเครื่องใหม่

---

## `docker-compose.yml`

```yaml
services:
  db:
    image: postgres:16
    env_file: .env
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d
    # ไม่เปิด port ออกนอก docker: api ต่อผ่าน db:5432 · เข้าฐานเองใช้ docker compose exec db psql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 3s
      retries: 20
  api:
    build: ./backend
    env_file: .env
    depends_on:
      db: { condition: service_healthy }
    volumes: ["./backend:/app"]
    ports: ["127.0.0.1:8000:8000"]  # /docs เปิดจากเครื่องนี้ มือถือเข้าผ่าน 5173 (proxy ภายใน)
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --reload"
  web:
    image: node:22
    working_dir: /web
    volumes: ["./frontend:/web", "/web/node_modules"]
    ports: ["5173:5173"]
    command: sh -c "npm install && npm run dev -- --host"
    depends_on: [api]
volumes:
  pgdata:
```

- `depends_on: condition: service_healthy` api รอจน Postgres รับ connection ได้จริง
- `./db/init` → `/docker-entrypoint-initdb.d` Postgres รันไฟล์ในนั้นให้**ครั้งเดียวตอนสร้าง volume ใหม่** (สร้างฐานเทสต์)
- `./backend:/app` โค้ดในเครื่องกับในคอนเทนเนอร์เป็นไฟล์เดียวกัน `--reload` เห็นทันทีที่แก้
- `/web/node_modules` เป็น volume เปล่าซ้อนทับ กัน `node_modules` ของ Windows ปนกับของ Linux
- `$$POSTGRES_USER` สองดอลลาร์ เพราะ compose กินไปหนึ่งตัว

## `.env.example` → copy เป็น `.env`

```ini
POSTGRES_USER=garage
POSTGRES_PASSWORD=garage
POSTGRES_DB=garage
DATABASE_URL=postgresql+psycopg://garage:garage@db:5432/garage
TEST_DATABASE_URL=postgresql+psycopg://garage:garage@db:5432/garage_test
JWT_SECRET=change-me-to-a-long-random-string
JWT_EXPIRE_MINUTES=720
ADMIN_USERNAME=
ADMIN_PASSWORD=
```

- `.env.example` เข้า git (แม่แบบ) · `.env` **ห้ามเข้า git** (`.gitignore` กันไว้)
- ต้องกรอกเอง: `JWT_SECRET` (ยาว ๆ สุ่ม ๆ) · `ADMIN_USERNAME` · `ADMIN_PASSWORD` (≥ 6 ตัว) — เว้นว่างหรือใช้ค่าตัวอย่าง api จะไม่ยอมเริ่ม (เฟส 1)
- ไม่ต้องใช้ python-dotenv เพราะ compose ใส่ env ให้ทุก service

## `db/init/01-test-db.sql`

```sql
create database garage_test;
```

ฐานแยกให้ pytest ล้างได้ทุกเทสต์โดยไม่แตะข้อมูลจริง

## `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

copy `requirements.txt` ก่อนโค้ด — Docker cache เป็นชั้น แก้โค้ดอย่างเดียวไม่ต้องลงแพ็กเกจใหม่

## `backend/requirements.txt`

```
fastapi>=0.115
uvicorn[standard]>=0.30
sqlalchemy>=2.0.30
psycopg[binary]>=3.2
alembic>=1.13
pydantic>=2.8
pyjwt>=2.8
pytest>=8
httpx>=0.27
pwdlib[argon2]>=0.2
ruff>=0.6
```

- `pwdlib[argon2]` แทน passlib (เลิกพัฒนาแล้ว และพังกับ bcrypt รุ่นใหม่)
- บรรทัดสุดท้ายต้องขึ้นบรรทัดใหม่ ไม่งั้นต่อท้ายไฟล์แล้วสองแพ็กเกจติดกัน

## `backend/pytest.ini` · `backend/alembic.ini` · `backend/ruff.toml`

```ini
[pytest]
pythonpath = .
testpaths = tests
```

```ini
[alembic]
script_location = %(here)s/alembic
prepend_sys_path = .
path_separator = os
```

```toml
line-length = 120
# ไฟล์ migration alembic สร้างให้ ไม่ต้องจัด
extend-exclude = ["alembic/versions"]

[lint]
# B008: Depends() ใน default argument เป็นวิธีปกติของ FastAPI
# FURB157: test ตั้งใจส่ง Decimal จาก string
# EXE002: โฟลเดอร์ Windows ที่ mount เข้า Docker ทุกไฟล์ดูเหมือน executable
ignore = ["B008", "FURB157", "EXE002"]

[lint.isort]
# มีโฟลเดอร์ backend/alembic/ ชื่อชน ruff จะเดาว่า alembic เป็นโค้ดเรา
known-third-party = ["alembic"]
```

- `pythonpath = .` ให้เทสต์ `import app...` ได้
- ruff บรรทัดยาวสุด 120 (เท่า Prettier) · ปิด B008 เพราะ `Depends()` ใน default คือท่าปกติของ FastAPI

## `backend/alembic/env.py`

```python
import os

from alembic import context
from sqlalchemy import create_engine

import app.models  # noqa: F401  (ลงทะเบียนตารางทั้งหมด)
from app.db import Base

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
```

`import app.models` ให้ alembic เห็นทุกตาราง ตอน `--autogenerate` จะได้เทียบกับฐานจริงได้

## `backend/tests/test_health.py`

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health():
    assert TestClient(app).get("/api/health").json() == {"ok": True}
```

เทสต์แรกไว้เช็คว่าโครงเทสต์ทำงาน (endpoint `/api/health` อยู่ใน `app/main.py` เฟส 1)

## `frontend/package.json`

```json
{
  "name": "garage-web",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "format": "prettier --write src"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.103.2",
    "axios": "^1.12.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-hook-form": "^7.88.0",
    "react-router-dom": "^7.0.0"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.0.0",
    "@vitejs/plugin-react": "^5.0.0",
    "prettier": "^3.9.8",
    "tailwindcss": "^4.0.0",
    "vite": "^7.0.0"
  }
}
```

| แพ็กเกจ | ใช้ทำอะไร |
|---|---|
| react · react-dom · react-router-dom | หน้าจอ + URL |
| @tanstack/react-query | ดึงข้อมูล + cache + โหลดใหม่หลังบันทึก |
| react-hook-form | เก็บค่าในฟอร์ม |
| axios | ยิง HTTP (ใช้ใน `api.js` ที่เดียว) |
| tailwindcss · @tailwindcss/vite | CSS (v4 ไม่มี `tailwind.config.js` ตั้งสีใน CSS เลย) |
| prettier | จัดรูปแบบโค้ด |

ไม่มี UI / icon / state library อื่น — ทุกตัวที่เพิ่มคือของที่ต้องดูแลต่อ

## `frontend/vite.config.js`

```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { "/api": "http://api:8000" }, watch: { usePolling: true } },
});
```

- proxy `/api` → `http://api:8000` หน้าเว็บเรียก path เดียวกับตัวเอง ไม่เจอ CORS ไม่ต้องตั้ง base URL
- `usePolling: true` จำเป็นบน Windows: ไฟล์ที่ mount เข้า docker ไม่ส่งสัญญาณว่าถูกแก้

## `frontend/.prettierrc` · `frontend/index.html`

```json
{ "printWidth": 120 }
```

```html
<!doctype html>
<html lang="th">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <title>ระบบจัดการอู่ซ่อมรถ</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

`lang="th"` + ฟอนต์ IBM Plex Sans Thai · `src/main.jsx` กับ `src/index.css` ตัวจริงอยู่ในเฟส 1

---

## เช็คว่าเสร็จ

```
curl http://localhost:8000/api/health            # {"ok":true}
docker compose exec api python -m pytest -q      # test_health ผ่าน
```

เปิด http://localhost:5173 เห็นหน้าเว็บ · http://localhost:8000/docs เห็นเอกสาร API

ติดปัญหา → ตาราง "เวลาติด" ใน [commands.md](commands.md)
