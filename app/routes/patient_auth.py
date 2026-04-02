# app/routes/patient_auth.py
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
from app.core.database import get_ref
from app.core.security import create_access_token, verify_token_header, verify_password

router = APIRouter(prefix="/patient-auth", tags=["Patient Auth"])


class PatientLoginRequest(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    password: str


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


@router.post("/login")
def patient_login(request: PatientLoginRequest):
    """Patient login by phone or email with password."""
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
    """Get all doctors linked to this patient."""
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
    """Get all active doctors (for booking)."""
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
    """Get all medical records for the logged-in patient."""
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


@router.post("/book-token")
def book_token_patient(
    doctor_id: str,
    appointment_time: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    patient_id = verify_token_header(authorization)
    if not patient_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from app.services.queue_service import get_all_active_queue_for_patient, book_token

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

    if appointment_time:
        try:
            entry_ref = get_ref(f"queue_entries/{entry['id']}")
            entry_ref.update({"appointment_time": appointment_time})
        except Exception:
            pass

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