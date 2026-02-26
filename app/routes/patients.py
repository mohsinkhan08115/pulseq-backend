from fastapi import APIRouter, HTTPException, status, Depends, Header, Query
from typing import Optional
from app.core.security import verify_token_header
from app.schemas.patient import PatientResponse, PatientSearchResponse, PatientCreate
from app.core.database import get_ref
from app.services.patient_service import (
    search_patients, get_patient_by_id, has_doctor_access,
    create_patient, link_doctor_to_patient, get_all_doctor_patients
)

router = APIRouter(prefix="/patients", tags=["Patients"])

def get_doctor_id(authorization: Optional[str] = Header(None)) -> str:
    doctor_id = verify_token_header(authorization)
    if not doctor_id:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return doctor_id

@router.get("/search", response_model=PatientSearchResponse)
def search(
    query: str = Query(..., min_length=1),
    search_type: str = Query("name"),
    doctor_id: str = Depends(get_doctor_id),
):
    patients = search_patients(query, search_type, doctor_id)
    return PatientSearchResponse(success=True, count=len(patients), patients=patients)

@router.get("/my-patients", response_model=PatientSearchResponse)
def my_patients(doctor_id: str = Depends(get_doctor_id)):
    patients = get_all_doctor_patients(doctor_id)
    return PatientSearchResponse(success=True, count=len(patients), patients=patients)

@router.post("/", response_model=PatientResponse, status_code=201)
def add_patient(data: PatientCreate, doctor_id: str = Depends(get_doctor_id)):
    patient = create_patient(
        name=data.name,
        email=data.email,
        phone=data.phone,
        date_of_birth=data.date_of_birth,
        location=data.location,
        medical_history_summary=data.medical_history_summary,
    )
    link_doctor_to_patient(doctor_id, patient["id"])
    return patient

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: str, doctor_id: str = Depends(get_doctor_id)):
    patient = get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not has_doctor_access(doctor_id, patient_id):
        raise HTTPException(status_code=403, detail="No access to this patient")
    return patient

@router.post("/{patient_id}/link")
def link_patient(patient_id: str, doctor_id: str = Depends(get_doctor_id)):
    patient = get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    link_doctor_to_patient(doctor_id, patient_id)
    return {"success": True, "message": "Patient linked successfully"}