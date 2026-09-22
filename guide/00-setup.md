# เฟส 0 — ติดตั้งและตั้งโครง

**จบเฟสนี้แล้ว** `docker compose up` ขึ้นครบ 3 ตัว · เปิด http://localhost:8000/api/health เห็น `{"ok":true}` · เปิด http://localhost:5173 เห็นหน้าเว็บ

ทั้งเฟสเป็น config ล้วน ไม่มี logic ให้คิด แต่ตั้งผิดตรงนี้จะไปเจ็บตอนเฟสหลัง

## ติดตั้งลงเครื่อง (ทำครั้งเดียว)

| โปรแกรม | เอาไว้ทำอะไร | ติดตั้งยังไง |
|---|---|---|
| Docker Desktop | รัน db + api + web ทั้งหมด | โหลดจาก docker.com เปิดทิ้งไว้ตอนทำงาน |
| Git | เก็บประวัติโค้ด | `winget install Git.Git` |
| VS Code | เขียนโค้ด | `winget install Microsoft.VisualStudioCode` |

**ไม่ต้องลง Python ไม่ต้องลง Node ลงเครื่อง** ทุกอย่างรันใน Docker
ข้อดีคือเครื่องไม่รก และย้ายไปเครื่องไหนก็ได้ผลเหมือนกัน
เช็คว่าพร้อม: `docker --version` กับ `docker compose version` ต้องขึ้นเลขเวอร์ชัน

## โครงโฟลเดอร์

```
project/
  .env  .env.example  .gitignore  docker-compose.yml
  db/init/01-test-db.sql
  backend/
    Dockerfile  requirements.txt  alembic.ini  pytest.ini  ruff.toml
    app/__init__.py  app/main.py  app/db.py  app/models.py
    alembic/env.py  alembic/script.py.mako  alembic/versions/.gitkeep
    tests/test_health.py
  frontend/
    package.json  vite.config.js  index.html  .prettierrc
    src/main.jsx  src/index.css
```

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
    ports: ["5432:5432"]
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
    ports: ["8000:8000"]
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

**ทำไมถึงเขียนแบบนี้**

- **`db` มี healthcheck และ `api` รอ `service_healthy`** — Postgres ใช้เวลาสักพักกว่าจะรับ connection ถ้าไม่รอ `alembic upgrade head` จะพังทุกครั้งที่เปิดเครื่องใหม่
- **`./db/init` map เข้า `/docker-entrypoint-initdb.d`** — Postgres รันไฟล์ในนั้นให้อัตโนมัติ **ครั้งเดียวตอนสร้าง volume ใหม่** ใช้สร้างฐาน `garage_test` ให้ pytest
- **`volumes: ["./backend:/app"]`** — โค้ดในเครื่องกับในคอนเทนเนอร์เป็นตัวเดียวกัน แก้แล้ว `--reload` เห็นทันที ไม่ต้อง build ใหม่
- **`/web/node_modules` เป็น volume เปล่าซ้อนทับ** — กัน `node_modules` ของ Windows ทับของในคอนเทนเนอร์ แพ็กเกจบางตัวคอมไพล์ตาม OS ปนกันแล้วพังแบบหาสาเหตุยาก
- **`alembic upgrade head` อยู่ในคำสั่งเริ่ม api** — ฐานข้อมูลตามโค้ดเสมอ ไม่มีวันลืมรัน migration
- **`$$POSTGRES_USER` มีสองดอลลาร์** — compose กิน `$` ไปหนึ่งตัว ที่เหลือส่งให้ shell ในคอนเทนเนอร์

## `.env.example` และ `.env`

```
POSTGRES_USER=garage
POSTGRES_PASSWORD=garage
POSTGRES_DB=garage
DATABASE_URL=postgresql+psycopg://garage:garage@db:5432/garage
TEST_DATABASE_URL=postgresql+psycopg://garage:garage@db:5432/garage_test
JWT_SECRET=change-me-to-a-long-random-string
JWT_EXPIRE_MINUTES=720
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin1234
```

`.env.example` เข้า git · `.env` **ห้ามเข้า** (`.gitignore` กันไว้แล้ว)

```
cp .env.example .env
```
แล้วแก้ `JWT_SECRET` ในไฟล์ `.env` เป็นอะไรก็ได้ที่ยาว ๆ สุ่ม ๆ

- **ทำไมต้องมีสองไฟล์** คนที่ clone ไปต้องรู้ว่าต้องตั้งตัวแปรอะไรบ้าง แต่ต้องไม่ได้ค่าจริง
- **ทำไม host ใน `DATABASE_URL` เป็น `db`** ในเครือข่ายของ compose ชื่อ service คือชื่อเครื่อง ไม่ใช่ `localhost`
- **ทำไมมี `TEST_DATABASE_URL` แยก** pytest ล้างทุกตารางก่อนทุกเทสต์ ถ้าชี้ฐานเดียวกับของจริงคือข้อมูลหายเกลี้ยง
- **`postgresql+psycopg://`** ไม่ใช่ `postgresql://` เพราะเราใช้ psycopg 3 ถ้าไม่ระบุ SQLAlchemy จะไปหา psycopg2 ที่ไม่ได้ลงไว้

## `.gitignore`

```
.env
__pycache__/
.pytest_cache/
node_modules/
dist/
guide/
.venv/
```

`guide/` คือโฟลเดอร์คู่มือนี้ ไม่ใช่โค้ดของระบบ เลยไม่เอาเข้า git
`.venv/` เผื่อสร้าง Python venv ในเครื่องไว้ให้ VS Code เดา type หรือรัน ruff นอก Docker (ไม่บังคับ)

## `db/init/01-test-db.sql`

```sql
create database garage_test;
```

## `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

**ทำไม copy `requirements.txt` ก่อน copy โค้ด** — Docker cache เป็นชั้น ๆ ถ้า copy ทุกอย่างพร้อมกัน แก้โค้ดบรรทัดเดียวก็ต้อง `pip install` ใหม่หมด แยกแบบนี้ชั้น pip ถูก cache ไว้จนกว่า requirements จะเปลี่ยน

## `backend/requirements.txt`

```
fastapi>=0.115
uvicorn[standard]>=0.30
sqlalchemy>=2.0.30
psycopg[binary]>=3.2
alembic>=1.13
pydantic>=2.8
pyjwt>=2.8
pwdlib[argon2]>=0.2
pytest>=8
httpx>=0.27
ruff>=0.6
```

**บรรทัดสุดท้ายของไฟล์ต้องขึ้นบรรทัดใหม่** ถ้าไม่มี แล้ววันหลังต่อท้ายด้วย `echo "x" >> requirements.txt` สองบรรทัดจะติดกันเป็น `httpx>=0.27ruff>=0.6` แล้ว `docker compose build` พัง (เคยเจอจริง)

| แพ็กเกจ | ทำไมต้องมี |
|---|---|
| fastapi + uvicorn | เว็บเซิร์ฟเวอร์ |
| sqlalchemy 2 + psycopg | คุยกับ Postgres |
| alembic | เปลี่ยนโครงฐานข้อมูลแบบมีประวัติ |
| pydantic 2 | ตรวจข้อมูลเข้า-ออก |
| pyjwt | token ล็อกอิน |
| pwdlib[argon2] | hash รหัสผ่านด้วย Argon2 (`[argon2]` ลง `argon2-cffi` ที่เป็นตัวคำนวณจริงมาด้วย) |
| pytest + httpx | เทสต์ (httpx เป็นตัวที่ `TestClient` ใช้ยิง request) |
| ruff | จัดรูปแบบโค้ด (`ruff format`) + หาจุดผิดที่เห็นได้โดยไม่ต้องรัน (`ruff check`) เช่น import ที่ไม่ได้ใช้ ตัวเดียวแทน black + isort + flake8 |

**ไม่ใช้ passlib** เลิกพัฒนาแล้ว และพังกับ bcrypt รุ่นใหม่ · `pwdlib` คือตัวที่เอกสาร FastAPI แนะนำแทน
**ไม่มี python-dotenv** เพราะ compose ใส่ env ให้ตั้งแต่แรก

## `backend/pytest.ini` และ `backend/alembic.ini`

```ini
[pytest]
pythonpath = .
testpaths = tests
```

`pythonpath = .` ทำให้ `import app.xxx` ในเทสต์ทำงานโดยไม่ต้องลงแพ็กเกจ

```ini
[alembic]
script_location = %(here)s/alembic
prepend_sys_path = .
path_separator = os
```

ไฟล์มาตรฐานของ alembic ยาวกว่านี้มาก ที่เหลือเป็นค่าที่เราไม่ใช้ (log config, url ที่เราอ่านจาก env เอง) ตัดทิ้งหมด

## `backend/ruff.toml`

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

- **`line-length = 120`** ค่าเริ่มต้นคือ 88 ซึ่งแคบไปสำหรับ query SQLAlchemy ที่ยาวอยู่แล้ว บรรทัดจะถูกหักจนอ่านยากกว่าเดิม
- **ปิด B008** ruff เตือน "อย่าเรียกฟังก์ชันใน default argument" ซึ่งถูกในโค้ด Python ทั่วไป แต่ `db=Depends(get_db)` คือวิธีที่ FastAPI ออกแบบมาให้เขียน
- **`extend-exclude = ["alembic/versions"]`** ไฟล์ migration alembic เขียนให้ ใช้รูปแบบของมันเอง ไม่ใช่โค้ดที่เราดูแล
- **ปิด EXE002** บน Windows โฟลเดอร์ที่ mount เข้าคอนเทนเนอร์ Linux ทุกไฟล์ถูกมองว่า "รันได้" ruff จะเตือนทุกไฟล์ว่าไม่มี `#!` บรรทัดแรก ซึ่งไม่ใช่ปัญหาจริง
- **`known-third-party = ["alembic"]`** ruff เรียง import เป็นสามกลุ่ม: stdlib · library ภายนอก · โค้ดเรา มันเห็นโฟลเดอร์ `backend/alembic/` แล้วเดาว่า `alembic` เป็นโค้ดเรา บรรทัดนี้บอกว่าเป็น library

ใช้ยังไง (รันในคอนเทนเนอร์ api):

```
docker compose run --rm api ruff check --fix .   # หาจุดผิด + แก้ที่แก้เองได้ (เช่นเรียง import)
docker compose run --rm api ruff format .        # จัดรูปแบบทุกไฟล์
```

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

- **ทำไมสั้นกว่าของที่ `alembic init` สร้างให้มาก** ของมาตรฐานรองรับ offline mode และอ่าน url จาก ini เราไม่ใช้ทั้งคู่
- **ทำไมต้อง `import app.models`** alembic เทียบ `Base.metadata` กับฐานจริง ถ้าไม่ import ตารางจะยังไม่ถูกลงทะเบียน มันจะคิดว่าไม่มีตารางอะไรเลยแล้วสั่ง **drop ทิ้งทั้งหมด**

`alembic/script.py.mako` เป็นแม่แบบของไฟล์ migration ใช้ของมาตรฐานจาก `alembic init` ได้เลย ไม่ต้องแก้

## `backend/app/db.py` และ `backend/app/models.py`

`env.py` import ทั้งสองไฟล์ และ `api` รัน `alembic upgrade head` ทุกครั้งที่เริ่ม **ถ้าไม่มีสองไฟล์นี้ api จะดับตั้งแต่เฟส 0**
ใส่แค่ขั้นต่ำที่ทำให้ import ได้ เฟส 1 ค่อยเติมของจริง

```python
# backend/app/db.py
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

engine = create_engine(os.environ["DATABASE_URL"])


class Base(DeclarativeBase):
    pass
```

```python
# backend/app/models.py  — ยังไม่มีตาราง เฟส 1 เริ่มที่ users
from app.db import Base  # noqa: F401
```

`backend/app/__init__.py` เป็นไฟล์ว่าง มีไว้ให้ Python มองโฟลเดอร์ `app` เป็นแพ็กเกจ

`backend/alembic/versions/` ต้องมีโฟลเดอร์อยู่ (ยังว่าง) ใส่ไฟล์ว่าง `.gitkeep` ไว้ git จะได้เก็บโฟลเดอร์นี้

ตอนนี้ `alembic upgrade head` ไม่มีอะไรให้ทำ แต่รันผ่าน = ท่อจาก compose → alembic → Postgres ต่อกันแล้ว

## `backend/app/main.py`

```python
from fastapi import FastAPI

app = FastAPI(title="ระบบจัดการอู่ซ่อมรถ")


@app.get("/api/health")
def health():
    """GET /api/health: เช็คว่าเซิร์ฟเวอร์ยังทำงาน"""
    return {"ok": True}
```

**docstring บรรทัดเดียวใต้ทุกฟังก์ชัน** เป็นกติกาของทั้งโปรเจ็ค: บอกว่าทำอะไร รับข้อมูลจากไหน ส่งไปไหน สั้น ๆ พอให้อ่านผ่านแล้วรู้เรื่องโดยไม่ต้องไล่โค้ด ฝั่ง JS ใช้ `//` บรรทัดเดียวเหนือฟังก์ชันแทน

## `backend/tests/test_health.py`

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health():
    assert TestClient(app).get("/api/health").json() == {"ok": True}
```

เทสต์แรกไม่ได้ทดสอบ logic อะไร มันทดสอบว่า **ท่อทั้งเส้นต่อกันแล้ว** — import ได้ แอปสร้างได้ route ตอบได้

---

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

| แพ็กเกจ | ทำไมต้องมี |
|---|---|
| react + react-dom + react-router-dom | หน้าจอ + เปลี่ยนหน้าตาม URL |
| vite + tailwind | รัน dev server / build · จัดหน้าด้วย class |
| axios | ตัวยิง request ใน `api.js` (เฟส 1) |
| **@tanstack/react-query** | **ดึงข้อมูลจาก backend และจำไว้ (cache)** — บันทึกอะไรแล้วสั่ง "ข้อมูลสินค้าเก่าแล้ว" ครั้งเดียว ทุกหน้าที่ใช้ข้อมูลนั้นโหลดใหม่เอง (เฟส 1) |
| **react-hook-form** | **เก็บค่าในฟอร์ม** — ใช้ `register("ชื่อฟิลด์")` แทนการเขียน `useState` + `onChange` เองทุกช่อง (เฟส 1) |
| prettier | จัดรูปแบบโค้ดหน้าจอ `npm run format` |

**ทำไมเลือกสองตัวที่ตัวหนา** — ระบบนี้ข้อมูลโยงกันเยอะ: รับของเข้า → Lot, คงเหลือ, สมุดสต็อก, สถานะ PO เปลี่ยนพร้อมกัน ถ้าเขียนเองต้องจำว่า "บันทึกแล้วต้องโหลดอะไรใหม่บ้าง" ทุกปุ่ม ลืมตัวเดียวคือหน้าจอโชว์เลขเก่าแบบไม่มีใครรู้ ส่วนฟอร์มบิลกับใบสั่งซื้อมีหลายแถวเพิ่ม/ลบได้ เขียนเองจะยุ่งเร็วมาก
ทั้งสองตัวเป็นของมาตรฐานที่คนเขียน React อ่านออกทันทีและมีเอกสารให้เปิด คุ้มกว่าเขียน hook เอง

**ของที่ไม่มี** — UI library, icon library, state library อื่น ทุกตัวที่เพิ่มคือของที่ต้องตามอัปเดตและต้องเข้าใจตอนมันพัง

## `frontend/.prettierrc`

```json
{ "printWidth": 120 }
```

ใช้ค่ามาตรฐานของ Prettier ทั้งหมด (double quote, มี `;`, ย่อหน้า 2 ช่อง) เปลี่ยนแค่ความยาวบรรทัดให้เท่ากับฝั่ง backend
ค่าเริ่มต้น 80 จะหัก JSX ที่มี className ยาว ๆ จนเกือบทุก element แตกเป็นหลายบรรทัด

**ทำไมต้องมีตัวจัดรูปแบบ** — ไม่ต้องเถียงหรือจำเรื่องย่อหน้า เว้นวรรค `;` อีกเลย ทุกไฟล์หน้าตาเหมือนกัน รัน `npm run format` ก่อน commit

**Tailwind v4 ไม่มี `tailwind.config.js`** และไม่ต้องลง postcss/autoprefixer แล้ว ตั้งสีใน CSS ผ่าน `@theme` แทน (เฟส 1)

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

- **proxy `/api` → `http://api:8000`** หน้าเว็บเรียก `/api/...` เป็น path เดียวกับตัวเอง เลยไม่เจอ CORS และไม่ต้องมีตัวแปร base url ให้ตั้งตอน deploy
- host เป็น `api` ไม่ใช่ `localhost` เพราะ vite รันในคอนเทนเนอร์ web คนละตัวกับ api
- **`usePolling: true`** Docker บน Windows ส่งสัญญาณไฟล์เปลี่ยนข้ามเครื่องไม่ได้ ถ้าไม่ poll แก้โค้ดแล้วหน้าเว็บจะนิ่งสนิท

## `frontend/index.html` · `src/main.jsx` · `src/index.css`

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

```jsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <p className="p-4 text-xl">อู่ซ่อมรถ</p>
  </StrictMode>,
);
```

```css
@import "tailwindcss";
```

`lang="th"` กับ `viewport` ใส่ตั้งแต่แรก เพราะทั้งระบบเป็นภาษาไทยและต้องใช้บนมือถือ
ฟอนต์ IBM Plex Sans Thai โหลดจาก Google Fonts เฟส 1 ตั้งเป็นฟอนต์หลักใน `index.css`

---

## คำสั่งของเฟสนี้

**ถ้าโฟลเดอร์นี้เคยรัน `docker compose up` มาก่อน** ฐานเก่ายังจำ migration ของโค้ดชุดก่อนไว้ เฟส 1 จะพังด้วย `Can't locate revision` ล้างทิ้งก่อนครั้งเดียว:

```
docker volume rm project_final_pgdata
```

```
cp .env.example .env
docker compose build api                              # ลง Python libs (ครั้งแรก 1-2 นาที)
docker compose run --rm --no-deps web npm install     # ลง Node libs
docker compose up -d
```

## เช็คว่าเฟสนี้เสร็จ

```
docker compose ps                      # api, db (healthy), web ขึ้นครบ
curl http://localhost:8000/api/health  # {"ok":true}
docker compose run --rm api pytest     # 1 passed
```

เปิด http://localhost:5173 เห็นคำว่า "อู่ซ่อมรถ" · เปิด http://localhost:8000/docs เห็นหน้าเอกสาร API ที่ FastAPI สร้างให้เอง

ติดตรงไหนดูตารางท้าย [commands.md](commands.md)

## git

```
docker compose run --rm api ruff format .
docker compose exec -T web npm run format
git add -A
git commit -m "chore: project scaffold"
```

(ครั้งแรกจริง ๆ ที่ยังไม่มี repo ให้ `git init` ก่อน)
