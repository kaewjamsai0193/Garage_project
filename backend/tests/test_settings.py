from app import models
from app.db import SessionLocal

SETTINGS = {"shop_name": "อู่ช่างเอ", "shop_address": "กรุงเทพฯ", "shop_tax_id": "0105555555555", "vat_rate": "7"}


def test_vat_rate_defaults_to_7():
    with SessionLocal() as s:
        assert s.get(models.Setting, 1).vat_rate == 7


def test_settings(client, h):
    r = client.put("/api/settings", json={**SETTINGS, "vat_rate": "10"}, headers=h["admin"])
    assert r.status_code == 200
    assert client.get("/api/settings", headers=h["employee"]).json()["vat_rate"] == "10.00"
    assert client.put("/api/settings", json=SETTINGS, headers=h["employee"]).status_code == 403
    assert client.put("/api/settings", json={**SETTINGS, "vat_rate": "-1"}, headers=h["admin"]).status_code == 422
    assert client.get("/api/settings", headers=h["mechanic"]).json()["shop_name"] == "อู่ช่างเอ"
