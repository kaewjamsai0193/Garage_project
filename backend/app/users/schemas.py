from typing import Literal

from pydantic import BaseModel, Field

from app.schemas import In, Out

Role = Literal["admin", "employee", "mechanic"]


class UserOut(Out):
    id: int
    username: str
    full_name: str
    role: Role
    is_active: bool


class LoginIn(In):
    username: str
    password: str


class LoginOut(BaseModel):
    access_token: str
    user: UserOut


class UserCreate(In):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    full_name: str = Field(min_length=1, max_length=100)
    role: Role
    password: str = Field(min_length=6)


class UserUpdate(In):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6)
