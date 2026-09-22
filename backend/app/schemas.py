from pydantic import BaseModel, ConfigDict


class In(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def serialize_for_role(user, admin_schema, schema, obj):
    """ต้นทุนออกจากเซิร์ฟเวอร์เฉพาะตอนที่คนขอเป็น admin"""
    return (admin_schema if user.role == "admin" else schema).model_validate(obj)
