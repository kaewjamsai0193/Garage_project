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
