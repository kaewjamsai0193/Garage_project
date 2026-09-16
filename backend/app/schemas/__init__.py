from pydantic import BaseModel, ConfigDict


class In(BaseModel):
    """Schema สำหรับรับข้อมูลจากผู้ใช้"""
    model_config = ConfigDict(str_strip_whitespace=True)


def by_role(user, admin_schema, schema, obj):
    """ เลือก schema ตามสิทธิ์ผู้ใช้ """
    return (admin_schema if user.role == "admin" else schema).model_validate(obj)