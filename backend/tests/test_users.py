def test_admin_creates_user_and_duplicate_rejected(client, headers):
    body = {"username": "somchai", "password": "secret1", "full_name": "สมชาย", "role": "mechanic"}
    r = client.post("/api/users", json=body, headers=headers["admin"])
    assert r.status_code == 201 and "password_hash" not in r.json()
    assert client.post("/api/users", json=body, headers=headers["admin"]).status_code == 409


def test_short_password_rejected(client, headers):
    body = {"username": "somsri", "password": "123", "full_name": "สมศรี", "role": "employee"}
    assert client.post("/api/users", json=body, headers=headers["admin"]).status_code == 422


def test_login_with_created_user_and_password_change(client, headers):
    uid = client.post(
        "/api/users",
        json={"username": "noi", "password": "secret1", "full_name": "น้อย", "role": "employee"},
        headers=headers["admin"],
    ).json()["id"]
    client.patch(f"/api/users/{uid}", json={"password": "secret2"}, headers=headers["admin"])
    assert client.post("/api/auth/login", json={"username": "noi", "password": "secret1"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "noi", "password": "secret2"}).status_code == 200


def test_only_admin_manages_users(client, headers):
    for role in ("employee", "mechanic"):
        assert client.get("/api/users", headers=headers[role]).status_code == 403


def test_admin_cannot_deactivate_or_demote_self(client, headers, users):
    url = f"/api/users/{users['admin'].id}"
    assert client.patch(url, json={"is_active": False}, headers=headers["admin"]).status_code == 409
    assert client.patch(url, json={"role": "employee"}, headers=headers["admin"]).status_code == 409


def test_deactivated_user_token_stops_working(client, headers, users):
    client.patch(f"/api/users/{users['employee'].id}", json={"is_active": False}, headers=headers["admin"])
    assert client.get("/api/auth/me", headers=headers["employee"]).status_code == 401
