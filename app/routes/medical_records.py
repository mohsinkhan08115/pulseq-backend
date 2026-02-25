from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from app.core.security import verify_token_header
from app.schemas.medical_record import (
    MedicalRecordCreate, MedicalRecordUpdate,
    MedicalRecordResponse, MedicalRecordsListResponse
)
from app.services.med_record_service import (
    get_medical_records, create_medical_record, update_medical_record
)
from app.services.patient_service import get_patient_by_id, has_doctor_access

router = APIRouter(prefix="/medical-records", tags=["Medical Records"])

def get_doctor_id(authorization: Optional[str] = Header(None)) -> str:
    doctor_id = verify_token_header(authorization)
    if not doctor_id:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return doctor_id

@router.get("/patient/{patient_id}", response_model=MedicalRecordsListResponse)
def list_records(patient_id: str, doctor_id: str = Depends(get_doctor_id)):
    patient = get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not has_doctor_access(doctor_id, patient_id):
        raise HTTPException(status_code=403, detail="No access to this patient's records")
    records = get_medical_records(patient_id, doctor_id)
    return MedicalRecordsListResponse(
        success=True, count=len(records),
        patient_name=patient["name"], records=records,
    )

@router.post("/", response_model=MedicalRecordResponse, status_code=201)
def create_record(data: MedicalRecordCreate, doctor_id: str = Depends(get_doctor_id)):
    if not get_patient_by_id(data.patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    record = create_medical_record(
        doctor_id=doctor_id, patient_id=data.patient_id,
        diagnosis=data.diagnosis, visit_date=data.visit_date,
        symptoms=data.symptoms, prescription=data.prescription,
        notes=data.notes, follow_up_date=data.follow_up_date,
        vital_signs=data.vital_signs,
    )
    return record

@router.patch("/{record_id}", response_model=MedicalRecordResponse)
def update_record(record_id: str, data: MedicalRecordUpdate, doctor_id: str = Depends(get_doctor_id)):
    record = update_medical_record(
        record_id, doctor_id,
        diagnosis=data.diagnosis, prescription=data.prescription,
        notes=data.notes, follow_up_date=data.follow_up_date,
        vital_signs=data.vital_signs,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Record not found or no permission")
    return record