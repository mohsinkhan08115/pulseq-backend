from fastapi import APIRouter, HTTPException, status, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import verify_token_header
from app.schemas.medical_record import (
    MedicalRecordCreate, MedicalRecordUpdate,
    MedicalRecordResponse, MedicalRecordsListResponse
)
from app.services.medical_record_service import (
    get_medical_records, create_medical_record, update_medical_record
)
from app.services.patient_service import get_patient_by_id, has_doctor_access

router = APIRouter(prefix="/medical-records", tags=["Medical Records"])

def get_doctor_id(authorization: Optional[str] = Header(None)) -> int:
    doctor_id = verify_token_header(authorization)
    if not doctor_id:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return doctor_id

def _record_to_response(r) -> MedicalRecordResponse:
    return MedicalRecordResponse(
        id=r.id,
        patient_id=r.patient_id,
        patient_name=r.patient.name,
        doctor_id=r.doctor_id,
        doctor_name=r.doctor.name,
        diagnosis=r.diagnosis,
        visit_date=r.visit_date,
        symptoms=r.symptoms or [],
        prescription=r.prescription,
        notes=r.notes,
        follow_up_date=r.follow_up_date,
        vital_signs=r.vital_signs,
    )

@router.get("/patient/{patient_id}", response_model=MedicalRecordsListResponse)
def list_records(
    patient_id: int,
    doctor_id: int = Depends(get_doctor_id),
    db: Session = Depends(get_db),
):
    """
    Get all medical records for a patient.
    Displays: patient name, diagnosis, date of visit, prescription, notes, vital signs.
    Only authorized doctors with prior consultation access can view.
    """
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not has_doctor_access(db, doctor_id, patient_id):
        raise HTTPException(status_code=403, detail="No access to this patient's records")

    records = get_medical_records(db, patient_id, doctor_id)
    return MedicalRecordsListResponse(
        success=True,
        count=len(records),
        patient_name=patient.name,
        records=[_record_to_response(r) for r in records],
    )

@router.post("/", response_model=MedicalRecordResponse, status_code=201)
def create_record(
    data: MedicalRecordCreate,
    doctor_id: int = Depends(get_doctor_id),
    db: Session = Depends(get_db),
):
    """Create a new medical record for a patient."""
    if not get_patient_by_id(db, data.patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")

    record = create_medical_record(
        db, doctor_id=doctor_id, patient_id=data.patient_id,
        diagnosis=data.diagnosis, visit_date=data.visit_date,
        symptoms=data.symptoms, prescription=data.prescription,
        notes=data.notes, follow_up_date=data.follow_up_date,
        vital_signs=data.vital_signs,
    )
    return _record_to_response(record)

@router.patch("/{record_id}", response_model=MedicalRecordResponse)
def update_record(
    record_id: int,
    data: MedicalRecordUpdate,
    doctor_id: int = Depends(get_doctor_id),
    db: Session = Depends(get_db),
):
    """Update a medical record. Only the creating doctor can update it."""
    record = update_medical_record(
        db, record_id, doctor_id,
        diagnosis=data.diagnosis, prescription=data.prescription,
        notes=data.notes, follow_up_date=data.follow_up_date,
        vital_signs=data.vital_signs,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Record not found or no permission")
    return _record_to_response(record)