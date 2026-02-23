from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
from app.models.models import QueueEntry

DEFAULT_AVG_DURATION = 15  # minutes

def get_active_queue_for_patient(db: Session, patient_id: int) -> Optional[QueueEntry]:
    return db.query(QueueEntry).filter(
        QueueEntry.patient_id == patient_id,
        QueueEntry.status.in_(["confirmed", "waiting", "serving"])
    ).first()

def get_current_serving_token(db: Session, doctor_id: int) -> int:
    entry = db.query(QueueEntry).filter(
        QueueEntry.doctor_id == doctor_id,
        QueueEntry.status == "serving"
    ).first()
    return entry.token_number if entry else 0

def get_next_token_number(db: Session, doctor_id: int) -> int:
    today = datetime.now().date()
    last = (
        db.query(QueueEntry)
        .filter(QueueEntry.doctor_id == doctor_id)
        .filter(QueueEntry.created_at >= today)
        .order_by(QueueEntry.token_number.desc())
        .first()
    )
    return (last.token_number + 1) if last else 1

def calculate_position(db: Session, entry: QueueEntry) -> int:
    ahead = db.query(QueueEntry).filter(
        QueueEntry.doctor_id == entry.doctor_id,
        QueueEntry.token_number < entry.token_number,
        QueueEntry.status.in_(["waiting", "serving"])
    ).count()
    return ahead + 1

def estimate_wait_time(db: Session, entry: QueueEntry) -> dict:
    """AI-based wait time estimation using peak-hour multiplier."""
    position = calculate_position(db, entry)
    avg_duration = DEFAULT_AVG_DURATION

    # Peak-hour multiplier
    hour = datetime.now().hour
    multiplier = 1.2 if hour in [9, 10, 11, 14, 15, 16] else 1.0

    patients_ahead = position - 1
    estimated = int(patients_ahead * avg_duration * multiplier)
    estimated += random.randint(2, 8)   # small buffer

    return {
        "estimated_minutes": estimated,
        "estimated_time": (datetime.now() + timedelta(minutes=estimated)).isoformat(),
        "consultation_duration": avg_duration,
        "patients_ahead": patients_ahead,
    }

def create_queue_entry(
    db: Session, patient_id: int, doctor_id: int, appointment_time: datetime
) -> QueueEntry:
    token = get_next_token_number(db, doctor_id)
    entry = QueueEntry(
        token_number=token, patient_id=patient_id,
        doctor_id=doctor_id, appointment_time=appointment_time,
        status="confirmed",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def check_in_patient(db: Session, patient_id: int) -> Optional[QueueEntry]:
    entry = get_active_queue_for_patient(db, patient_id)
    if not entry:
        return None
    entry.status = "waiting"
    entry.check_in_time = datetime.now()
    db.commit()
    db.refresh(entry)
    return entry

def start_consultation(db: Session, patient_id: int, doctor_id: int) -> Optional[QueueEntry]:
    entry = db.query(QueueEntry).filter(
        QueueEntry.patient_id == patient_id,
        QueueEntry.doctor_id == doctor_id,
        QueueEntry.status == "waiting"
    ).first()
    if not entry:
        return None
    entry.status = "serving"
    entry.consultation_start_time = datetime.now()
    db.commit()
    db.refresh(entry)
    return entry

def complete_consultation(db: Session, patient_id: int, doctor_id: int) -> Optional[QueueEntry]:
    entry = db.query(QueueEntry).filter(
        QueueEntry.patient_id == patient_id,
        QueueEntry.doctor_id == doctor_id,
        QueueEntry.status == "serving"
    ).first()
    if not entry:
        return None
    entry.status = "completed"
    entry.consultation_end_time = datetime.now()
    if entry.consultation_start_time:
        delta = entry.consultation_end_time - entry.consultation_start_time
        entry.actual_duration = int(delta.total_seconds() / 60)
    db.commit()
    db.refresh(entry)
    return entry

def get_doctor_queue(db: Session, doctor_id: int) -> List[QueueEntry]:
    return (
        db.query(QueueEntry)
        .filter(
            QueueEntry.doctor_id == doctor_id,
            QueueEntry.status.in_(["confirmed", "waiting", "serving"])
        )
        .order_by(QueueEntry.token_number)
        .all()
    )