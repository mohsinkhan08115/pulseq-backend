from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.core.security import verify_token_header
from app.schemas.queue import QueueCreate, QueueStatusResponse
from app.services.queue_service import (
    get_active_queue_for_patient, get_current_serving_token,
    calculate_position, ai_predict_wait_time, create_queue_entry,
    check_in_patient, start_consultation, complete_consultation,
    get_doctor_queue, book_token
)
from app.core.database import get_ref

router = APIRouter(prefix="/queue", tags=["Queue Management"])


class BookTokenRequest(BaseModel):
    patient_id: str
    doctor_id: str


def get_doctor_id(authorization: Optional[str] = Header(None)) -> str:
    doctor_id = verify_token_header(authorization)
    if not doctor_id:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return doctor_id


def _build_queue_dict(entry: dict, include_ai: bool = True) -> dict:
    doctor = get_ref(f"doctors/{entry['doctor_id']}").get() or {}
    patient = get_ref(f"patients/{entry['patient_id']}").get() or {}
    booking_type = entry.get("booking_type", "appointment")

    result = {
        "token_number": entry["token_number"],
        "patient_name": patient.get("name", ""),
        "doctor_name": doctor.get("name", ""),
        "current_serving_token": get_current_serving_token(entry["doctor_id"]),
        "position_in_queue": calculate_position(entry),
        "status": entry["status"],
        "booking_type": booking_type,
        "appointment_time": entry.get("appointment_time"),
        "check_in_time": entry.get("check_in_time"),
        "show_queue_status": booking_type == "token",
    }

    # Only include AI prediction for token-based bookings
    if booking_type == "token" and include_ai:
        result["estimated_wait_time"] = ai_predict_wait_time(entry)
    else:
        result["estimated_wait_time"] = None

    return result


@router.post("/book-token")
def book_token_endpoint(data: BookTokenRequest, doctor_id: str = Depends(get_doctor_id)):
    """Book a queue token with AI-predicted wait time."""
    result = book_token(data.patient_id, data.doctor_id)
    entry = result["entry"]
    prediction = result["ai_prediction"]

    doctor = get_ref(f"doctors/{entry['doctor_id']}").get() or {}
    patient = get_ref(f"patients/{entry['patient_id']}").get() or {}

    return {
        "success": True,
        "already_existed": result["already_exists"],
        "message": "You already have an active token" if result["already_exists"] else "Token booked successfully",
        "token_number": entry["token_number"],
        "booking_type": "token",
        "patient_name": patient.get("name", ""),
        "doctor_name": doctor.get("name", ""),
        "status": entry["status"],
        "show_queue_status": True,
        "ai_prediction": {
            "estimated_minutes": prediction["estimated_minutes"],
            "estimated_time": prediction["estimated_time"],
            "consultation_duration": prediction["consultation_duration"],
            "patients_ahead": prediction["patients_ahead"],
            "confidence_percent": prediction.get("confidence_percent", 75),
            "peak_hour": prediction.get("peak_hour", False),
        }
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
    entry = create_queue_entry(data.patient_id, data.doctor_id, appointment_dt,
                               booking_type="appointment")
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