# app/routes/patient_auth.py
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
    appointment_time: Optional[str] = None,  # optional appointment details
    authorization: Optional[str] = Header(None)
):
    """
    Book a walk-in queue token.
    - Returns AI wait prediction.
    - Prevents booking if patient already has an active token with ANY doctor.
    - Optionally accepts appointment_time for scheduling context.
    """
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from app.services.queue_service import get_all_active_queue_for_patient, book_token

    # ── Issue 2: Prevent double booking ───────────────────────────────────
    existing = get_all_active_queue_for_patient(patient_id)
    active = [
        e for e in existing
        if e.get("status") not in ("completed", "cancelled")
    ]
    if active:
        existing_doctor = get_ref(f"doctors/{active[0]['doctor_id']}").get() or {}
        raise HTTPException(
            status_code=409,
            detail=f"You already have an active token with Dr. {existing_doctor.get('name', 'another doctor')}. "
                   f"Please cancel it before booking a new one."
        )

    result = book_token(patient_id, doctor_id)
    entry = result["entry"]
    prediction = result["ai_prediction"]
    doctor = get_ref(f"doctors/{doctor_id}").get() or {}

    # Save appointment_time to the entry if provided
    if appointment_time:
        try:
            entry_ref = get_ref(f"queue/{entry['id']}")
            entry_ref.update({"appointment_time": appointment_time})
        except Exception:
            pass  # Non-critical, don't fail the booking

    return {
        "success": True,
        "already_existed": result["already_exists"],
        "message": "Token booked successfully",
        "token_number": entry["token_number"],
        "booking_type": "token",
        "doctor_name": doctor.get("name", ""),
        "doctor_specialization": doctor.get("specialization", ""),
        "appointment_time": appointment_time,
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


@router.get("/my-queue")
def my_queue(authorization: Optional[str] = Header(None)):
    """Get ALL patient queue entries across all doctors."""
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from app.services.queue_service import (
        get_all_active_queue_for_patient,
        get_current_serving_token,
        calculate_position,
        ai_predict_wait_time,
    )

    entries = get_all_active_queue_for_patient(patient_id)
    if not entries:
        return {"has_active_queue": False, "appointments": []}

    appointments = []
    for entry in entries:
        booking_type = entry.get("booking_type", "token")
        doctor = get_ref(f"doctors/{entry['doctor_id']}").get() or {}
        appointments.append({
            "entry_id": entry.get("id", ""),  # needed for cancel
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
            "estimated_wait_time": ai_predict_wait_time(entry) if booking_type == "token" else None,
        })

    return {"has_active_queue": True, "appointments": appointments}


@router.delete("/cancel")
def cancel_booking(
    entry_id: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    Cancel the patient's active token.
    - If entry_id is provided, cancels that specific booking.
    - Otherwise cancels the first active booking found.
    """
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from app.services.queue_service import get_all_active_queue_for_patient

    entries = get_all_active_queue_for_patient(patient_id)
    if not entries:
        raise HTTPException(status_code=404, detail="No active booking found")

    # Find the specific entry to cancel
    entry_to_cancel = None
    if entry_id:
        for e in entries:
            if e.get("id") == entry_id:
                entry_to_cancel = e
                break
        if not entry_to_cancel:
            raise HTTPException(status_code=404, detail="Booking not found")
    else:
        # Cancel the first active one
        active = [e for e in entries if e.get("status") not in ("completed", "cancelled")]
        if not active:
            raise HTTPException(status_code=404, detail="No active booking to cancel")
        entry_to_cancel = active[0]

    # Cannot cancel if already being served
    if entry_to_cancel.get("status") == "serving":
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel — consultation is already in progress"
        )

    # Update status to cancelled in database
    try:
        queue_ref = get_ref(f"queue/{entry_to_cancel['id']}")
        queue_ref.update({
            "status": "cancelled",
            "cancelled_at": __import__("datetime").datetime.utcnow().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel: {str(e)}")

    return {
        "success": True,
        "message": f"Token #{entry_to_cancel['token_number']} cancelled successfully"
    }