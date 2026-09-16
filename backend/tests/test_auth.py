def test_login_returns_token_and_user(client, users):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "pw"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "admin"
    assert "password_hash" not in r.json()["user"]      # ต้องไม่หลุด


def test_wrong_password(client, users):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "ผิด"})
    assert r.status_code == 401


def test_unknown_user_same_message_as_wrong_password(client, users):
    a = client.post("/api/auth/login", json={"username": "ไม่มีคนนี้", "password": "pw"})
    b = client.post("/api/auth/login", json={"username": "admin", "password": "ผิด"})
    assert a.json()["detail"] == b.json()["detail"]     # ห้ามบอกใบ้ว่าบัญชีไหนมีจริง


def test_no_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_deactivated_user_token_stops_working(client, users, h):
    client.patch(f"/api/users/{users['employee'].id}", json={"is_active": False}, headers=h["admin"])
    assert client.get("/api/auth/me", headers=h["employee"]).status_code == 401