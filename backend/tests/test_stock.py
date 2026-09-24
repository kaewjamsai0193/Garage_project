from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app import models
from app.db import SessionLocal

PRODUCT = {"code": "OIL-1", "name": "น้ำมันเครื่อง", "unit": "ลิตร", "sale_price": "250", "min_stock": "2"}


def opening(client, headers, pid, qty, cost):
    r = client.post(
        "/api/stock/opening",
        headers=headers["admin"],
        json={"product_id": pid, "qty": qty, "unit_cost": cost, "reason": "ตั้งต้น"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_product_create_list_and_unit_lock(client, headers):
    r = client.post("/api/products", json=PRODUCT, headers=headers["employee"])
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    duplicate = client.post("/api/products", json=PRODUCT, headers=headers["employee"])
    assert (duplicate.status_code, duplicate.json()["detail"]) == (409, "รหัสสินค้านี้มีแล้ว")  # service จับได้ ไม่ใช่ DB
    assert client.post("/api/products", json={**PRODUCT, "code": "X"}, headers=headers["mechanic"]).status_code == 403
    opening(client, headers, pid, "1.500", "180")
    [p] = client.get("/api/products", headers=headers["mechanic"]).json()
    assert Decimal(p["qty_on_hand"]) == Decimal("1.5")
    one = client.get(f"/api/products/{pid}", headers=headers["mechanic"]).json()
    assert one["code"] == "OIL-1" and Decimal(one["qty_on_hand"]) == Decimal("1.5")
    assert client.get("/api/products/999", headers=headers["mechanic"]).status_code == 404
    unit_change = client.put(f"/api/products/{pid}", json={**PRODUCT, "unit": "ขวด"}, headers=headers["admin"])
    assert unit_change.status_code == 409  # มีของเข้าคลังแล้ว เปลี่ยนหน่วยไม่ได้
    price_change = client.put(
        f"/api/products/{pid}", json={**PRODUCT, "sale_price": "260"}, headers=headers["employee"]
    )
    assert price_change.status_code == 200
    other = client.post("/api/products", json={**PRODUCT, "code": "OIL-2"}, headers=headers["employee"]).json()
    taken = client.put(f"/api/products/{other['id']}", json=PRODUCT, headers=headers["employee"])  # เอารหัสคนอื่น
    assert (taken.status_code, taken.json()["detail"]) == (409, "รหัสสินค้านี้มีแล้ว")


def test_lots_are_separate_and_oldest_first(client, headers, make_product):
    pid = make_product()
    opening(client, headers, pid, "2", "80")
    opening(client, headers, pid, "3", "120")
    lots = client.get(f"/api/products/{pid}/lots", headers=headers["admin"]).json()
    assert [Decimal(lot["unit_cost"]) for lot in lots] == [80, 120]
    [p] = client.get("/api/products", headers=headers["admin"]).json()
    assert Decimal(p["qty_on_hand"]) == 5


def test_adjustments_and_cost_visibility(client, headers, make_product):
    pid = make_product()
    lot_id = opening(client, headers, pid, "2", "100")
    up = {"product_id": pid, "qty": "1", "unit_cost": "1", "reason": "นับเจอ"}
    assert client.post("/api/stock/opening", json=up, headers=headers["employee"]).status_code == 403
    down = {"lot_id": lot_id, "qty": "1", "reason": "เสีย"}
    too_much = client.post("/api/stock/adjust-down", json={**down, "qty": "3"}, headers=headers["employee"])
    assert too_much.status_code == 409
    no_reason = client.post("/api/stock/adjust-down", json={**down, "reason": " "}, headers=headers["employee"])
    assert no_reason.status_code == 422
    assert client.post("/api/stock/adjust-down", json=down, headers=headers["mechanic"]).status_code == 403
    assert client.post("/api/stock/adjust-down", json=down, headers=headers["employee"]).status_code == 204
    [admin_lot] = client.get(f"/api/products/{pid}/lots", headers=headers["admin"]).json()
    [emp_lot] = client.get(f"/api/products/{pid}/lots", headers=headers["employee"]).json()
    assert Decimal(admin_lot["unit_cost"]) == 100 and Decimal(admin_lot["qty_remaining"]) == 1
    assert not {"unit_cost", "cost_total"} & emp_lot.keys()
    moves = client.get(f"/api/products/{pid}/movements", headers=headers["mechanic"]).json()
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
