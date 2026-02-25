from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from datetime import datetime
from app.core.security import verify_token_header
from app.schemas.queue import QueueCreate, QueueStatusResponse
from app.services.queue_service import (
    get_active_queue_for_patient, get_current_serving_token,
    calculate_position, estimate_wait_time, create_queue_entry,
    check_in_patient, start_consultation, complete_consultation, get_doctor_queue
)
from app.core.database import db

router = APIRouter(prefix="/queue", tags=["Queue Management"])

def get_doctor_id(authorization: Optional[str] = Header(None)) -> str:
    doctor_id = verify_token_header(authorization)
    if not doctor_id:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return doctor_id

def _build_queue_dict(entry: dict) -> dict:
    doctor_doc = db.collection("doctors").document(entry["doctor_id"]).get()
    doctor_name = doctor_doc.to_dict().get("name", "") if doctor_doc.exists else ""
    patient_doc = db.collection("patients").document(entry["patient_id"]).get()
    patient_name = patient_doc.to_dict().get("name", "") if patient_doc.exists else ""
    return {
        "token_number": entry["token_number"],
        "patient_name": patient_name,
        "doctor_name": doctor_name,
        "current_serving_token": get_current_serving_token(entry["doctor_id"]),
        "position_in_queue": calculate_position(entry),
        "status": entry["status"],
        "estimated_wait_time": estimate_wait_time(entry),
        "appointment_time": entry.get("appointment_time"),
        "check_in_time": entry.get("check_in_time"),
    }

@router.get("/status", response_model=QueueStatusResponse)
def queue_status(patient_id: str, doctor_id: str = Depends(get_doctor_id)):
    entry = get_active_queue_for_patient(patient_id)
    if not entry:
        return QueueStatusResponse(success=True, has_active_queue=False)
    return QueueStatusResponse(success=True, has_active_queue=True,
                               queue_data=_build_queue_dict(entry))

@router.get("/doctor-queue")
def doctor_queue(doctor_id: str = Depends(get_doctor_id)):
    entries = get_doctor_queue(doctor_id)
    return {"success": True, "count": len(entries), "queue": entries}

@router.get("/{patient_id}")
def queue_details(patient_id: str, doctor_id: str = Depends(get_doctor_id)):
    entry = get_active_queue_for_patient(patient_id)
    if not entry:
        raise HTTPException(status_code=404, detail="No active queue entry for this patient")
    return {"success": True, **_build_queue_dict(entry)}

@router.post("/create")
def create_queue(data: QueueCreate, doctor_id: str = Depends(get_doctor_id)):
    try:
        appointment_dt = datetime.fromisoformat(data.appointment_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid appointment_time — use ISO format")
    entry = create_queue_entry(data.patient_id, data.doctor_id, appointment_dt)
    return {"success": True, "message": "Added to queue", "token_number": entry["token_number"]}

@router.post("/check-in/{patient_id}")
def check_in(patient_id: str, doctor_id: str = Depends(get_doctor_id)):
    entry = check_in_patient(patient_id)
    if not entry:
        raise HTTPException(status_code=404, detail="No active queue entry")
    return {"success": True, "message": "Patient checked in"}

@router.post("/start/{patient_id}")
def start(patient_id: str, doctor_id: str = Depends(get_doctor_id)):
    entry = start_consultation(patient_id, doctor_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Patient not in waiting status")
    return {"success": True, "message": "Consultation started"}

@router.post("/complete/{patient_id}")
def complete(patient_id: str, doctor_id: str = Depends(get_doctor_id)):
    entry = complete_consultation(patient_id, doctor_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Patient not in serving status")
    return {"success": True, "message": "Consultation completed",
            "duration_minutes": entry.get("actual_duration")}