from pydantic import BaseModel
from typing import List, Optional, Dict

class MedicalRecordCreate(BaseModel):
    patient_id: str
    diagnosis: str
    visit_date: str
    symptoms: List[str]
    prescription: str
    notes: str
    follow_up_date: Optional[str] = None
    vital_signs: Optional[Dict[str, str]] = None

class MedicalRecordUpdate(BaseModel):
    diagnosis: Optional[str] = None
    prescription: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[str] = None
    vital_signs: Optional[Dict[str, str]] = None

class MedicalRecordResponse(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    doctor_id: str
    doctor_name: str
    diagnosis: str
    visit_date: str
    symptoms: List[str]
    prescription: str
    notes: str
    follow_up_date: Optional[str] = None
    vital_signs: Optional[Dict[str, str]] = None

    class Config:
        from_attributes = True

class MedicalRecordsListResponse(BaseModel):
    success: bool
    count: int
    patient_name: str
    records: List[MedicalRecordResponse]