from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import In

Role = Literal["admin", "employee", "mechanic"]

class UserOut(BaseModel):
    """Schema สำหรับส่งข้อมูลผู้ใช้"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str
    role: Role
    is_active: bool

class UserCreate(In):
    """Schema สำหรับสร้างผู้ใช้ใหม่"""
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    full_name: str = Field(min_length=1, max_length=100)
    role: Role
    password: str = Field(min_length=6)

class UserUpdate(In):
    """Schema สำหรับแก้ไขผู้ใช้"""
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6)

class LoginIn(In):
    """Schema สำหรับรับข้อมูลเข้าสู่ระบบ"""
    username: str
    password: str

class LoginOut(BaseModel):
    """Schema สำหรับส่งข้อมูลเข้าสู่ระบบ"""
    access_token: str
    user: UserOut

class SettingsIn(In):
    """Schema สำหรับแก้ไขตั้งค่าร้าน"""
    shop_name: str = Field(max_length=200)
    shop_address: str
    shop_tax_id: str = Field(max_length=20)
    vat_rate: Decimal = Field(ge=0, le=100, decimal_places=2)
    repair_warranty_days: int = Field(ge=0)
    dead_stock_days: int = Field(gt=0)

class SettingsOut(SettingsIn):
    """Schema สำหรับส่งข้อมูลตั้งค่าร้าน"""
    model_config = ConfigDict(from_attributes=True)