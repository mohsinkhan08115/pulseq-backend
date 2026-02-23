from fastapi import APIRouter, HTTPException, status, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import verify_token_header
from app.schemas.queue import QueueCreate, QueueStatusResponse
from app.services.queue_service import (
    get_active_queue_for_patient, get_current_serving_token,
    calculate_position, estimate_wait_time,
    create_queue_entry, check_in_patient,
    start_consultation, complete_consultation, get_doctor_queue
)

router = APIRouter(prefix="/queue", tags=["Queue Management"])

def get_doctor_id(authorization: Optional[str] = Header(None)) -> int:
    doctor_id = verify_token_header(authorization)
    if not doctor_id:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return doctor_id

def _build_queue_dict(db, entry) -> dict:
    return {
        "token_number": entry.token_number,
        "patient_name": entry.patient.name,
        "doctor_name": entry.doctor.name,
        "current_serving_token": get_current_serving_token(db, entry.doctor_id),
        "position_in_queue": calculate_position(db, entry),
        "status": entry.status,
        "estimated_wait_time": estimate_wait_time(db, entry),
        "appointment_time": entry.appointment_time.isoformat(),
        "check_in_time": entry.check_in_time.isoformat() if entry.check_in_time else None,
    }

@router.get("/status", response_model=QueueStatusResponse)
def queue_status(
    patient_id: int,
    doctor_id: int = Depends(get_doctor_id),
    db: Session = Depends(get_db),
):
    """Get patient's current queue status with estimated wait time."""
    entry = get_active_queue_for_patient(db, patient_id)
    if not entry:
        return QueueStatusResponse(success=True, has_active_queue=False)
    return QueueStatusResponse(
        success=True, has_active_queue=True,
        queue_data=_build_queue_dict(db, entry)
    )

@router.get("/doctor-queue")
def doctor_queue(
    doctor_id: int = Depends(get_doctor_id),
    db: Session = Depends(get_db),
):
    """Get full active queue for the logged-in doctor."""
    entries = get_doctor_queue(db, doctor_id)
    return {
        "success": True,
        "count": len(entries),
        "queue": [
            {
                "id": e.id,
                "token_number": e.token_number,
                "patient_id": e.patient_id,
                "patient_name": e.patient.name,
                "status": e.status,
                "appointment_time": e.appointment_time.isoformat(),
                "check_in_time": e.check_in_time.isoformat() if e.check_in_time else None,
            }
            for e in entries
        ],
    }

@router.get("/{patient_id}")
def queue_details(
    patient_id: int,
    doctor_id: int = Depends(get_doctor_id),
    db: Session = Depends(get_db),
):
    """Detailed queue info including token, position and estimated wait time."""
    entry = get_active_queue_for_patient(db, patient_id)
    if not entry:
        raise HTTPException(status_code=404, detail="No active queue entry for this patient")
    return {"success": True, **_build_queue_dict(db, entry)}

@router.post("/create")
def create_queue(
    data: QueueCreate,
    doctor_id: int = Depends(get_doctor_id),
    db: Session = Depends(get_db),
):
    """Add a patient to the doctor's queue."""
    try:
        appointment_dt = datetime.fromisoformat(data.appointment_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid appointment_time — use ISO format")
    entry = create_queue_entry(db, data.patient_id, data.doctor_id, appointment_dt)
    return {"success": True, "message": "Added to queue", "token_number": entry.token_number}

@router.post("/check-in/{patient_id}")
def check_in(
    patient_id: int,
    doctor_id: int = Depends(get_doctor_id),
    db: Session = Depends(get_db),
):
    """Patient has arrived — mark as waiting."""
    entry = check_in_patient(db, patient_id)
    if not entry:
        raise HTTPException(status_code=404, detail="No active queue entry")
    return {"success": True, "message": "Patient checked in"}

@router.post("/start/{patient_id}")
def start(
    patient_id: int,
    doctor_id: int = Depends(get_doctor_id),
    db: Session = Depends(get_db),
):
    """Start consultation — status changes to serving."""
    entry = start_consultation(db, patient_id, doctor_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Patient not in waiting status")
    return {"success": True, "message": "Consultation started"}

@router.post("/complete/{patient_id}")
def complete(
    patient_id: int,
    doctor_id: int = Depends(get_doctor_id),
    db: Session = Depends(get_db),
):
    """Complete consultation — records actual duration."""
    entry = complete_consultation(db, patient_id, doctor_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Patient not in serving status")
    return {
        "success": True,
        "message": "Consultation completed",
        "duration_minutes": entry.actual_duration
    }