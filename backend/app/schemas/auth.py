
from pydantic import BaseModel, EmailStr, Field


class Register(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class Login(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class UserProfile(BaseModel):
    id: str
    email: EmailStr
    role: str
    active: bool
