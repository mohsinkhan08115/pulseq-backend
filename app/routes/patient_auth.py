# app/routes/patient_auth.py
from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from app.core.database import get_ref
from app.core.security import create_access_token, verify_token_header, verify_password

router = APIRouter(prefix="/patient-auth", tags=["Patient Auth"])

MINIMUM_BOOKING_GAP_MINUTES = 15


class PatientLoginRequest(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    password: str


class MultiTokenRequest(BaseModel):
    doctor_ids: List[str]
    slot_duration_minutes: int = 15


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
        "patient_number": patient.get("patient_number"),
    }


def _check_booking_gap(patient_id: str) -> Optional[int]:
    """
    Check if patient made a booking in the last 15 minutes.
    Returns minutes remaining if gap not met, None if OK to book.
    """
    all_entries = get_ref("queue_entries").get() or {}
    now = datetime.now(timezone.utc)
    min_gap = timedelta(minutes=MINIMUM_BOOKING_GAP_MINUTES)

    latest_booking_time = None
    for entry in all_entries.values():
        if entry.get("patient_id") != patient_id:
            continue
        raw = entry.get("appointment_time") or entry.get("created_at")
        if not raw:
            continue
        try:
            t = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if latest_booking_time is None or t > latest_booking_time:
                latest_booking_time = t
        except Exception:
            continue

    if latest_booking_time is None:
        return None  # No previous booking, OK

    elapsed = now - latest_booking_time
    if elapsed < min_gap:
        remaining = int((min_gap - elapsed).total_seconds() / 60) + 1
        return remaining
    return None


@router.post("/login")
def patient_login(request: PatientLoginRequest):
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
            hashed = patient.get("hashed_password")
            if not hashed or not verify_password(request.password, hashed):
                raise HTTPException(status_code=401, detail="Incorrect password")
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


@router.get("/my-doctors")
def get_my_doctors(authorization: Optional[str] = Header(None)):
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    all_links = get_ref("doctor_patient").get() or {}
    doctor_ids = [
        link["doctor_id"]
        for link in all_links.values()
        if link.get("patient_id") == patient_id
    ]

    doctors = []
    for doc_id in doctor_ids:
        doc = get_ref(f"doctors/{doc_id}").get()
        if doc and doc.get("is_active", True):
            doctors.append({
                "id": doc_id,
                "name": doc.get("name", ""),
                "specialization": doc.get("specialization", ""),
                "hospital": doc.get("hospital", ""),
                "phone": doc.get("phone", ""),
                "email": doc.get("email", ""),
            })

    return {"doctors": doctors}


@router.get("/doctors")
def get_all_doctors(authorization: Optional[str] = Header(None)):
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


@router.get("/my-records")
def get_my_records(authorization: Optional[str] = Header(None)):
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    patient = get_ref(f"patients/{patient_id}").get()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    all_records = get_ref("medical_records").get() or {}
    records = []
    for rec_id, record in all_records.items():
        if record.get("patient_id") != patient_id:
            continue
        doc = get_ref(f"doctors/{record.get('doctor_id', '')}").get() or {}
        records.append({
            "id": rec_id,
            "patient_id": patient_id,
            "patient_name": patient.get("name", ""),
            "doctor_id": record.get("doctor_id", ""),
            "doctor_name": doc.get("name", ""),
            "doctor_specialization": doc.get("specialization", ""),
            "diagnosis": record.get("diagnosis", ""),
            "visit_date": record.get("visit_date", ""),
            "symptoms": record.get("symptoms", []),
            "prescription": record.get("prescription", ""),
            "notes": record.get("notes", ""),
            "follow_up_date": record.get("follow_up_date"),
            "vital_signs": record.get("vital_signs"),
        })

    records.sort(key=lambda x: x.get("visit_date", ""), reverse=True)
    return {
        "success": True,
        "count": len(records),
        "patient_name": patient.get("name", ""),
        "records": records,
    }


@router.get("/queue-preview")
def queue_preview(
    doctor_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Get estimated wait time for a doctor WITHOUT booking.
    Used to show wait time before the patient confirms booking.
    """
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from app.services.queue_service import get_next_token_number, ai_predict_wait_time, get_historical_avg_duration
    from app.core.database import get_ref as _ref
    from datetime import datetime, timezone
    import uuid

    doctor = _ref(f"doctors/{doctor_id}").get() or {}
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Build a fake entry to get prediction without saving
    token = get_next_token_number(doctor_id)
    fake_entry = {
        "token_number": token,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "confirmed",
        "booking_type": "token",
        "date": datetime.now(timezone.utc).date().isoformat(),
    }
    prediction = ai_predict_wait_time(fake_entry)
    avg_duration = get_historical_avg_duration(doctor_id)

    return {
        "doctor_name": doctor.get("name", ""),
        "doctor_specialization": doctor.get("specialization", ""),
        "next_token": token,
        "estimated_wait_minutes": prediction["estimated_minutes"],
        "estimated_time": prediction["estimated_time"],
        "patients_ahead": prediction["patients_ahead"],
        "consultation_duration": int(avg_duration),
        "confidence_percent": prediction.get("confidence_percent", 75),
        "peak_hour": prediction.get("peak_hour", False),
    }


@router.post("/book-token")
def book_token_patient(
    doctor_id: str,
    appointment_time: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    Book a single token with a doctor.
    Rules:
    - Patient must wait 15 minutes between any two bookings.
    - Multiple bookings with same or different doctors are allowed after the gap.
    """
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Check 15-minute gap between bookings
    minutes_remaining = _check_booking_gap(patient_id)
    if minutes_remaining is not None:
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {minutes_remaining} more minute(s) before booking again. "
                   f"A minimum {MINIMUM_BOOKING_GAP_MINUTES}-minute gap is required between bookings."
        )

    from app.services.queue_service import book_token

    result = book_token(patient_id, doctor_id)
    entry = result["entry"]
    prediction = result["ai_prediction"]
    doctor = get_ref(f"doctors/{doctor_id}").get() or {}
    patient = get_ref(f"patients/{patient_id}").get() or {}

    if appointment_time:
        try:
            get_ref(f"queue_entries/{entry['id']}").update({"appointment_time": appointment_time})
        except Exception:
            pass

    return {
        "success": True,
        "already_existed": False,
        "message": "Token booked successfully",
        "token_number": entry["token_number"],
        "booking_type": "token",
        "patient_name": patient.get("name", ""),
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


@router.post("/book-multi-token")
def book_multi_token_patient(
    data: MultiTokenRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Book tokens with multiple doctors sequentially.
    Same 15-minute gap rule applies.
    """
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not data.doctor_ids:
        raise HTTPException(status_code=400, detail="doctor_ids list cannot be empty")

    minutes_remaining = _check_booking_gap(patient_id)
    if minutes_remaining is not None:
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {minutes_remaining} more minute(s) before booking again."
        )

    from app.services.queue_service import book_multi_doctor_token

    results = book_multi_doctor_token(
        patient_id=patient_id,
        doctor_ids=data.doctor_ids,
        slot_duration=data.slot_duration_minutes,
    )

    return {
        "success": True,
        "total_bookings": len(results),
        "bookings": results,
        "message": f"Successfully booked {len(results)} token(s)",
    }


@router.get("/my-queue")
def my_queue(authorization: Optional[str] = Header(None)):
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
            "entry_id": entry.get("id", ""),
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
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from app.services.queue_service import get_all_active_queue_for_patient

    entries = get_all_active_queue_for_patient(patient_id)
    if not entries:
        raise HTTPException(status_code=404, detail="No active booking found")

    entry_to_cancel = None
    if entry_id:
        for e in entries:
            if e.get("id") == entry_id:
                entry_to_cancel = e
                break
        if not entry_to_cancel:
            raise HTTPException(status_code=404, detail="Booking not found")
    else:
        active = [e for e in entries if e.get("status") not in ("completed", "cancelled")]
        if not active:
            raise HTTPException(status_code=404, detail="No active booking to cancel")
        entry_to_cancel = active[0]

    if entry_to_cancel.get("status") == "serving":
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel — consultation is already in progress"
        )

    try:
        queue_ref = get_ref(f"queue_entries/{entry_to_cancel['id']}")
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