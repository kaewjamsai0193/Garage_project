from app import models
from app.db import SessionLocal

SETTINGS = {"shop_name": "อู่ช่างเอ", "shop_address": "กรุงเทพฯ", "shop_tax_id": "0105555555555", "vat_rate": "7"}


def test_vat_rate_defaults_to_7():
    with SessionLocal() as s:
        assert s.get(models.Setting, 1).vat_rate == 7


def test_settings(client, headers):
    r = client.put("/api/settings", json={**SETTINGS, "vat_rate": "10"}, headers=headers["admin"])
    assert r.status_code == 200
    assert client.get("/api/settings", headers=headers["employee"]).json()["vat_rate"] == "10.00"
    assert client.put("/api/settings", json=SETTINGS, headers=headers["employee"]).status_code == 403
    assert client.put("/api/settings", json={**SETTINGS, "vat_rate": "-1"}, headers=headers["admin"]).status_code == 422
    assert client.get("/api/settings", headers=headers["mechanic"]).json()["shop_name"] == "อู่ช่างเอ"
