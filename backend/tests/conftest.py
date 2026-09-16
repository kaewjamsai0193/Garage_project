import os

os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import models  # noqa: E402
from app.auth import create_token, hash_password  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def migrated():
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def clean(migrated):
    with engine.begin() as conn:
        conn.execute(text(f"truncate {', '.join(Base.metadata.tables)} restart identity cascade"))
        conn.execute(text("insert into settings (id) values (1)"))


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