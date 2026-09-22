from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas import In, Out


class ProductIn(In):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    unit: str = Field(min_length=1, max_length=20)
    sale_price: Decimal = Field(ge=0, decimal_places=4)
    min_stock: Decimal = Field(default=Decimal(0), ge=0, decimal_places=3)
    is_active: bool = True


class ProductOut(ProductIn, Out):
    id: int
    qty_on_hand: Decimal


class LotOut(Out):
    id: int
    product_id: int
    source_type: str
    qty_received: Decimal
    qty_remaining: Decimal
    created_at: datetime


class LotAdminOut(LotOut):
    unit_cost: Decimal
    cost_total: Decimal


class MovementOut(BaseModel):
    id: int
    lot_id: int
    qty: Decimal
    movement_type: str
    reason: str | None
    created_by_name: str
    created_at: datetime


class AdjustDownIn(In):
    lot_id: int
    qty: Decimal = Field(gt=0, decimal_places=3)
    reason: str = Field(min_length=1)


class AdjustUpIn(In):
    product_id: int
    qty: Decimal = Field(gt=0, decimal_places=3)
    unit_cost: Decimal = Field(ge=0, decimal_places=4)
    reason: str = Field(min_length=1)
    source_type: Literal["adjustment", "opening"]
