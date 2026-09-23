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
