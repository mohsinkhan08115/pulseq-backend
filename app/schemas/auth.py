from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    password: str

class RegisterDoctorRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    specialization: str
    hospital: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    doctor: dict