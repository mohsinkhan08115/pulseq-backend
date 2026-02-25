from typing import List, Optional
from app.core.database import get_ref
from datetime import datetime, timedelta
import uuid
import random

DEFAULT_AVG_DURATION = 15


def get_active_queue_for_patient(patient_id: str) -> Optional[dict]:
    all_entries = get_ref("queue_entries").get() or {}
    for entry_id, entry in all_entries.items():
        if (entry.get("patient_id") == patient_id and
                entry.get("status") in ["confirmed", "waiting", "serving"]):
            entry["id"] = entry_id
            return entry
    return None


def get_current_serving_token(doctor_id: str) -> int:
    all_entries = get_ref("queue_entries").get() or {}
    for entry in all_entries.values():
        if entry.get("doctor_id") == doctor_id and entry.get("status") == "serving":
            return entry.get("token_number", 0)
    return 0


def get_next_token_number(doctor_id: str) -> int:
    today = datetime.now().date().isoformat()
    all_entries = get_ref("queue_entries").get() or {}
    tokens = [
        e.get("token_number", 0)
        for e in all_entries.values()
        if e.get("doctor_id") == doctor_id and e.get("date") == today
    ]
    return max(tokens) + 1 if tokens else 1


def calculate_position(entry: dict) -> int:
    all_entries = get_ref("queue_entries").get() or {}
    ahead = sum(
        1 for e in all_entries.values()
        if (e.get("doctor_id") == entry["doctor_id"] and
            e.get("status") in ["waiting", "serving"] and
            e.get("token_number", 0) < entry.get("token_number", 0))
    )
    return ahead + 1


def estimate_wait_time(entry: dict) -> dict:
    position = calculate_position(entry)
    hour = datetime.now().hour
    multiplier = 1.2 if hour in [9, 10, 11, 14, 15, 16] else 1.0
    patients_ahead = position - 1
    estimated = int(patients_ahead * DEFAULT_AVG_DURATION * multiplier)
    estimated += random.randint(2, 8)
    return {
        "estimated_minutes": estimated,
        "estimated_time": (datetime.now() + timedelta(minutes=estimated)).isoformat(),
        "consultation_duration": DEFAULT_AVG_DURATION,
        "patients_ahead": patients_ahead,
    }


def create_queue_entry(patient_id: str, doctor_id: str, appointment_time: datetime) -> dict:
    today = datetime.now().date().isoformat()
    token = get_next_token_number(doctor_id)
    entry_id = str(uuid.uuid4())
    entry_data = {
        "token_number": token,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_time": appointment_time.isoformat(),
        "status": "confirmed",
        "check_in_time": None,
        "consultation_start_time": None,
        "consultation_end_time": None,
        "actual_duration": None,
        "date": today,
    }
    get_ref(f"queue_entries/{entry_id}").set(entry_data)
    entry_data["id"] = entry_id
    return entry_data


def check_in_patient(patient_id: str) -> Optional[dict]:
    entry = get_active_queue_for_patient(patient_id)
    if not entry:
        return None
    get_ref(f"queue_entries/{entry['id']}").update({
        "status": "waiting",
        "check_in_time": datetime.now().isoformat(),
    })
    entry["status"] = "waiting"
    return entry


def start_consultation(patient_id: str, doctor_id: str) -> Optional[dict]:
    all_entries = get_ref("queue_entries").get() or {}
    for entry_id, entry in all_entries.items():
        if (entry.get("patient_id") == patient_id and
                entry.get("doctor_id") == doctor_id and
                entry.get("status") == "waiting"):
            get_ref(f"queue_entries/{entry_id}").update({
                "status": "serving",
                "consultation_start_time": datetime.now().isoformat(),
            })
            entry["id"] = entry_id
            entry["status"] = "serving"
            return entry
    return None


def complete_consultation(patient_id: str, doctor_id: str) -> Optional[dict]:
    all_entries = get_ref("queue_entries").get() or {}
    for entry_id, entry in all_entries.items():
        if (entry.get("patient_id") == patient_id and
                entry.get("doctor_id") == doctor_id and
                entry.get("status") == "serving"):
            end_time = datetime.now()
            duration = None
            if entry.get("consultation_start_time"):
                start = datetime.fromisoformat(entry["consultation_start_time"])
                duration = int((end_time - start).total_seconds() / 60)
            get_ref(f"queue_entries/{entry_id}").update({
                "status": "completed",
                "consultation_end_time": end_time.isoformat(),
                "actual_duration": duration,
            })
            entry["id"] = entry_id
            entry["status"] = "completed"
            entry["actual_duration"] = duration
            return entry
    return None


def get_doctor_queue(doctor_id: str) -> List[dict]:
    all_entries = get_ref("queue_entries").get() or {}
    entries = []
    for entry_id, entry in all_entries.items():
        if (entry.get("doctor_id") == doctor_id and
                entry.get("status") in ["confirmed", "waiting", "serving"]):
            entry["id"] = entry_id
            patient = get_ref(f"patients/{entry['patient_id']}").get() or {}
            entry["patient_name"] = patient.get("name", "")
            entries.append(entry)
    entries.sort(key=lambda x: x.get("token_number", 0))
    return entries