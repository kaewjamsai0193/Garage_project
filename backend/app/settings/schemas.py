from decimal import Decimal

from pydantic import Field

from app.schemas import In, Out


class SettingsIn(In):
    shop_name: str = Field(max_length=200)
    shop_address: str
    shop_tax_id: str = Field(max_length=20)
    vat_rate: Decimal = Field(ge=0, le=100, decimal_places=2)


class SettingsOut(SettingsIn, Out):
    pass
