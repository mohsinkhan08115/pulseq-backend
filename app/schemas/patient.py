from pydantic import BaseModel, EmailStr
from typing import List, Optional

class PatientCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    date_of_birth: str
    location: str
    medical_history_summary: Optional[str] = None

class PatientResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    date_of_birth: str
    location: str
    total_visits: int = 0
    last_visit: Optional[str] = None
    medical_history_summary: Optional[str] = None

    class Config:
        from_attributes = True

class PatientSearchResponse(BaseModel):
    success: bool
    count: int
    patients: List[PatientResponse]