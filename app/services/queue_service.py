from typing import List, Optional
from app.core.database import get_ref
from datetime import datetime, timedelta
import uuid
import random
import statistics

DEFAULT_AVG_DURATION = 15
PEAK_HOURS = [9, 10, 11, 14, 15, 16]


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


def get_historical_avg_duration(doctor_id: str) -> float:
    """AI: Calculate predicted avg consultation duration from historical data."""
    all_entries = get_ref("queue_entries").get() or {}
    durations = [
        e.get("actual_duration")
        for e in all_entries.values()
        if e.get("doctor_id") == doctor_id
        and e.get("actual_duration") is not None
        and isinstance(e.get("actual_duration"), (int, float))
        and 2 <= e.get("actual_duration", 0) <= 120  # Sanity bounds
    ]
    if len(durations) >= 3:
        avg = statistics.median(durations)
        return max(5.0, min(60.0, avg))
    return float(DEFAULT_AVG_DURATION)


def ai_predict_wait_time(entry: dict) -> dict:
    """
    AI-powered wait time prediction using multiple factors:
    1. Historical consultation durations (median-based, outlier-resistant)
    2. Peak hour multiplier  
    3. Day-of-week patterns
    4. Queue depth weighting
    """
    doctor_id = entry["doctor_id"]
    position = calculate_position(entry)
    patients_ahead = position - 1

    # Factor 1: Historical AI-learned average
    avg_duration = get_historical_avg_duration(doctor_id)

    # Factor 2: Peak hour multiplier
    hour = datetime.now().hour
    day_of_week = datetime.now().weekday()

    if hour in PEAK_HOURS:
        time_multiplier = 1.3
    elif hour in [12, 13]:  # Lunch hour slowdown
        time_multiplier = 0.85
    else:
        time_multiplier = 1.0

    # Factor 3: Day-of-week pattern (Mon/Fri/Sat busier)
    if day_of_week in [0, 4]:
        day_multiplier = 1.1
    elif day_of_week == 5:  # Saturday
        day_multiplier = 1.2
    else:
        day_multiplier = 1.0

    # Factor 4: Queue depth efficiency loss
    all_entries = get_ref("queue_entries").get() or {}
    today = datetime.now().date().isoformat()
    total_today = sum(
        1 for e in all_entries.values()
        if e.get("doctor_id") == doctor_id
        and e.get("date") == today
        and e.get("status") in ["waiting", "serving", "confirmed"]
    )
    depth_factor = 1.0 + (min(total_today, 20) * 0.01)

    # Calculate AI estimate
    base_estimate = patients_ahead * avg_duration
    ai_estimate = base_estimate * time_multiplier * day_multiplier * depth_factor

    # Small uncertainty buffer
    uncertainty = ai_estimate * random.uniform(-0.05, 0.08)
    final_estimate = max(0, int(ai_estimate + uncertainty))

    # Confidence score based on historical data volume
    all_durations_count = sum(
        1 for e in all_entries.values()
        if e.get("doctor_id") == doctor_id and e.get("actual_duration") is not None
    )
    confidence = min(95, 60 + (all_durations_count * 2))

    return {
        "estimated_minutes": final_estimate,
        "estimated_time": (datetime.now() + timedelta(minutes=final_estimate)).isoformat(),
        "consultation_duration": int(avg_duration),
        "patients_ahead": patients_ahead,
        "confidence_percent": confidence,
        "peak_hour": hour in PEAK_HOURS,
        "ai_factors": {
            "historical_avg_mins": round(avg_duration, 1),
            "time_multiplier": time_multiplier,
            "day_multiplier": day_multiplier,
            "depth_factor": round(depth_factor, 2),
        }
    }


# Keep legacy function for backward compatibility
def estimate_wait_time(entry: dict) -> dict:
    return ai_predict_wait_time(entry)


def book_token(patient_id: str, doctor_id: str) -> dict:
    """Book a token for patient - token-based queue booking with AI prediction."""
    # Check if patient already has active token booking
    existing = get_active_queue_for_patient(patient_id)
    if existing and existing.get("booking_type") == "token":
        prediction = ai_predict_wait_time(existing)
        return {"already_exists": True, "entry": existing, "ai_prediction": prediction}

    appointment_time = datetime.now()
    token = get_next_token_number(doctor_id)
    entry_id = str(uuid.uuid4())
    today = datetime.now().date().isoformat()

    entry_data = {
        "token_number": token,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_time": appointment_time.isoformat(),
        "status": "confirmed",
        "booking_type": "token",
        "check_in_time": None,
        "consultation_start_time": None,
        "consultation_end_time": None,
        "actual_duration": None,
        "date": today,
    }
    get_ref(f"queue_entries/{entry_id}").set(entry_data)
    entry_data["id"] = entry_id

    ai_prediction = ai_predict_wait_time(entry_data)

    return {
        "already_exists": False,
        "entry": entry_data,
        "ai_prediction": ai_prediction
    }


def create_queue_entry(patient_id: str, doctor_id: str, appointment_time: datetime,
                       booking_type: str = "appointment") -> dict:
    today = datetime.now().date().isoformat()
    token = get_next_token_number(doctor_id)
    entry_id = str(uuid.uuid4())
    entry_data = {
        "token_number": token,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_time": appointment_time.isoformat(),
        "status": "confirmed",
        "booking_type": booking_type,
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