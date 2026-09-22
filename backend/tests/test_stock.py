from decimal import Decimal as D

import pytest
from sqlalchemy.exc import IntegrityError

from app import models
from app.db import SessionLocal

PRODUCT = {"code": "OIL-1", "name": "น้ำมันเครื่อง", "unit": "ลิตร", "sale_price": "250", "min_stock": "2"}


def opening(client, h, pid, qty, cost):
    r = client.post(
        "/api/stock/adjust-up",
        headers=h["admin"],
        json={"product_id": pid, "qty": qty, "unit_cost": cost, "reason": "ตั้งต้น", "source_type": "opening"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_product_create_search_and_unit_lock(client, h):
    r = client.post("/api/products", json=PRODUCT, headers=h["employee"])
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert client.post("/api/products", json=PRODUCT, headers=h["employee"]).status_code == 409
    assert client.post("/api/products", json={**PRODUCT, "code": "X"}, headers=h["mechanic"]).status_code == 403
    opening(client, h, pid, "1.500", "180")
    [p] = client.get("/api/products?q=น้ำมัน", headers=h["mechanic"]).json()
    assert D(p["qty_on_hand"]) == D("1.5")
    one = client.get(f"/api/products/{pid}", headers=h["mechanic"]).json()
    assert one["code"] == "OIL-1" and D(one["qty_on_hand"]) == D("1.5")
    assert client.get("/api/products/999", headers=h["mechanic"]).status_code == 404
    assert client.put(f"/api/products/{pid}", json={**PRODUCT, "unit": "ขวด"}, headers=h["admin"]).status_code == 409
    assert (
        client.put(f"/api/products/{pid}", json={**PRODUCT, "sale_price": "260"}, headers=h["employee"]).status_code
        == 200
    )


def test_lots_are_separate_and_oldest_first(client, h, make_product):
    pid = make_product()
    opening(client, h, pid, "2", "80")
    opening(client, h, pid, "3", "120")
    lots = client.get(f"/api/products/{pid}/lots", headers=h["admin"]).json()
    assert [D(lot["unit_cost"]) for lot in lots] == [80, 120]
    [p] = client.get("/api/products", headers=h["admin"]).json()
    assert D(p["qty_on_hand"]) == 5


def test_adjustments_and_cost_visibility(client, h, make_product):
    pid = make_product()
    lot_id = opening(client, h, pid, "2", "100")
    up = {"product_id": pid, "qty": "1", "unit_cost": "1", "reason": "นับเจอ", "source_type": "adjustment"}
    assert client.post("/api/stock/adjust-up", json=up, headers=h["employee"]).status_code == 403
    down = {"lot_id": lot_id, "qty": "1", "reason": "เสีย"}
    assert client.post("/api/stock/adjust-down", json={**down, "qty": "3"}, headers=h["employee"]).status_code == 409
    assert client.post("/api/stock/adjust-down", json={**down, "reason": " "}, headers=h["employee"]).status_code == 422
    assert client.post("/api/stock/adjust-down", json=down, headers=h["mechanic"]).status_code == 403
    assert client.post("/api/stock/adjust-down", json=down, headers=h["employee"]).status_code == 204
    [admin_lot] = client.get(f"/api/products/{pid}/lots", headers=h["admin"]).json()
    [emp_lot] = client.get(f"/api/products/{pid}/lots", headers=h["employee"]).json()
    assert D(admin_lot["unit_cost"]) == 100 and D(admin_lot["qty_remaining"]) == 1
    assert not {"unit_cost", "cost_total"} & emp_lot.keys()
    moves = client.get(f"/api/products/{pid}/movements", headers=h["mechanic"]).json()
    assert [m["movement_type"] for m in moves] == ["adjust", "opening"]
    assert moves[0]["created_by_name"] == "employee"


def test_lot_qty_cannot_go_negative(users, make_product):
    with SessionLocal() as s:
        s.add(
            models.StockLot(
                product_id=make_product(),
                source_type="opening",
                unit_cost=1,
                qty_received=1,
                qty_remaining=-1,
                cost_total=1,
                created_by=users["admin"].id,
            )
        )
        with pytest.raises(IntegrityError):
            s.flush()
