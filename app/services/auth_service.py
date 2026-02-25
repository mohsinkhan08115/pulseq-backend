from typing import Optional
from app.core.database import get_ref
from app.core.security import verify_password, get_password_hash, create_access_token
import uuid


def authenticate_doctor(phone: Optional[str], email: Optional[str], password: str) -> Optional[dict]:
    doctors = get_ref("doctors").get() or {}
    for doc_id, doctor in doctors.items():
        if not doctor.get("is_active", True):
            continue
        if email and doctor.get("email") == email:
            if verify_password(password, doctor["hashed_password"]):
                doctor["id"] = doc_id
                return doctor
        elif phone and doctor.get("phone") == phone:
            if verify_password(password, doctor["hashed_password"]):
                doctor["id"] = doc_id
                return doctor
    return None


def register_doctor(name: str, email: str, phone: str,
                    specialization: str, hospital: str, password: str) -> dict:
    doctor_id = str(uuid.uuid4())
    doctor_data = {
        "name": name,
        "email": email,
        "phone": phone,
        "specialization": specialization,
        "hospital": hospital,
        "hashed_password": get_password_hash(password),
        "is_active": True,
    }
    get_ref(f"doctors/{doctor_id}").set(doctor_data)
    doctor_data["id"] = doctor_id
    return doctor_data


def create_token_for_doctor(doctor_id: str) -> str:
    return create_access_token(data={"sub": str(doctor_id)})


def get_doctor_by_id(doctor_id: str) -> Optional[dict]:
    data = get_ref(f"doctors/{doctor_id}").get()
    if data:
        data["id"] = doctor_id
    return data