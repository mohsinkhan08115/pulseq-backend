# app/routes/patient_auth.py  (NEW FILE)
# Patient-facing authentication and booking endpoints

from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
from app.core.database import get_ref
from app.core.security import create_access_token, verify_token_header

router = APIRouter(prefix="/patient-auth", tags=["Patient Auth"])


class PatientLoginRequest(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None


def _patient_to_dict(patient_id: str, patient: dict) -> dict:
    return {
        "id": patient_id,
        "name": patient.get("name", ""),
        "email": patient.get("email", ""),
        "phone": patient.get("phone", ""),
        "date_of_birth": patient.get("date_of_birth", ""),
        "location": patient.get("location", ""),
        "total_visits": patient.get("total_visits", 0),
        "last_visit": patient.get("last_visit"),
        "medical_history_summary": patient.get("medical_history_summary"),
    }


@router.post("/login")
def patient_login(request: PatientLoginRequest):
    """Patient login by phone or email - no password needed."""
    if not request.phone and not request.email:
        raise HTTPException(status_code=400, detail="Provide email or phone")

    all_patients = get_ref("patients").get() or {}
    for patient_id, patient in all_patients.items():
        if not patient.get("is_active", True):
            continue
        match = (
            (request.email and patient.get("email") == request.email) or
            (request.phone and patient.get("phone") == request.phone)
        )
        if match:
            token = create_access_token(data={"sub": patient_id, "role": "patient"})
            return {
                "access_token": token,
                "token_type": "bearer",
                "role": "patient",
                "patient": _patient_to_dict(patient_id, patient),
            }

    raise HTTPException(
        status_code=404,
        detail="Patient not found. Please contact your doctor to register."
    )


@router.get("/me")
def get_profile(authorization: Optional[str] = Header(None)):
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    patient = get_ref(f"patients/{patient_id}").get()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return _patient_to_dict(patient_id, patient)


@router.get("/doctors")
def get_doctors(authorization: Optional[str] = Header(None)):
    """All available doctors for patient to choose from."""
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    all_doctors = get_ref("doctors").get() or {}
    return {
        "doctors": [
            {
                "id": doc_id,
                "name": doc.get("name", ""),
                "specialization": doc.get("specialization", ""),
                "hospital": doc.get("hospital", ""),
            }
            for doc_id, doc in all_doctors.items()
            if doc.get("is_active", True)
        ]
    }


@router.post("/book-token")
def book_token_patient(
    doctor_id: str,
    authorization: Optional[str] = Header(None)
):
    """Book a walk-in token. Returns AI wait prediction."""
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from app.services.queue_service import book_token
    result = book_token(patient_id, doctor_id)
    entry = result["entry"]
    prediction = result["ai_prediction"]
    doctor = get_ref(f"doctors/{doctor_id}").get() or {}

    return {
        "success": True,
        "already_existed": result["already_exists"],
        "message": "You already have an active token" if result["already_exists"] else "Token booked successfully",
        "token_number": entry["token_number"],
        "booking_type": "token",
        "doctor_name": doctor.get("name", ""),
        "doctor_specialization": doctor.get("specialization", ""),
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


@router.post("/book-appointment")
def book_appointment_patient(
    doctor_id: str,
    appointment_time: str,
    authorization: Optional[str] = Header(None)
):
    """Book a scheduled appointment. No AI queue prediction for appointments."""
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from app.services.queue_service import create_queue_entry
    from datetime import datetime

    try:
        appointment_dt = datetime.fromisoformat(appointment_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid appointment_time format")

    entry = create_queue_entry(patient_id, doctor_id, appointment_dt, booking_type="appointment")
    doctor = get_ref(f"doctors/{doctor_id}").get() or {}

    return {
        "success": True,
        "message": "Appointment booked successfully",
        "token_number": entry["token_number"],
        "booking_type": "appointment",
        "doctor_name": doctor.get("name", ""),
        "appointment_time": appointment_time,
        "show_queue_status": False,  # NO AI prediction for appointments
    }


@router.get("/my-queue")
def my_queue(authorization: Optional[str] = Header(None)):
    """Get patient's current queue status. AI prediction only for token bookings."""
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from app.services.queue_service import (
        get_active_queue_for_patient, get_current_serving_token,
        calculate_position, ai_predict_wait_time,
    )

    entry = get_active_queue_for_patient(patient_id)
    if not entry:
        return {"has_active_queue": False}

    booking_type = entry.get("booking_type", "appointment")
    doctor = get_ref(f"doctors/{entry['doctor_id']}").get() or {}

    response = {
        "has_active_queue": True,
        "token_number": entry["token_number"],
        "doctor_name": doctor.get("name", ""),
        "doctor_specialization": doctor.get("specialization", ""),
        "current_serving_token": get_current_serving_token(entry["doctor_id"]),
        "position_in_queue": calculate_position(entry),
        "status": entry["status"],
        "booking_type": booking_type,
        "show_queue_status": booking_type == "token",
        "appointment_time": entry.get("appointment_time"),
        "check_in_time": entry.get("check_in_time"),
        # AI prediction ONLY for token bookings
        "estimated_wait_time": ai_predict_wait_time(entry) if booking_type == "token" else None,
    }
    return response