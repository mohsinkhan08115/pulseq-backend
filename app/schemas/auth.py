from pydantic import BaseModel, EmailStr
from typing import Optional, Dict

class LoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str

    # Optional: validation to ensure at least one of email or phone is provided
    def validate_login(self):
        if not self.email and not self.phone:
            raise ValueError("Either email or phone must be provided")

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
    doctor: Dict  # or you can define a Doctor schema later