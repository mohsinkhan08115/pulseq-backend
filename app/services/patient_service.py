from typing import List, Optional
from app.core.database import get_ref
import uuid

def has_doctor_access(doctor_id: str, patient_id: str) -> bool:
    link = get_ref(f"doctor_patient/{doctor_id}_{patient_id}").get()
    return link is not None

def link_doctor_to_patient(doctor_id: str, patient_id: str):
    if not has_doctor_access(doctor_id, patient_id):
        get_ref(f"doctor_patient/{doctor_id}_{patient_id}").set({
            "doctor_id": doctor_id,
            "patient_id": patient_id,
        })

def get_patient_by_id(patient_id: str) -> Optional[dict]:
    data = get_ref(f"patients/{patient_id}").get()
    if data:
        data["id"] = patient_id
    return data

def get_all_doctor_patients(doctor_id: str) -> List[dict]:
    all_links = get_ref("doctor_patient").get() or {}
    patients = []
    for key, link in all_links.items():
        if link.get("doctor_id") == doctor_id:
            patient = get_patient_by_id(link["patient_id"])
            if patient and patient.get("is_active", True):
                patients.append(patient)
    return patients

def search_patients(query: str, search_type: str, doctor_id: str) -> List[dict]:
    all_patients = get_all_doctor_patients(doctor_id)
    query_stripped = query.strip()
    query_nospace = query_stripped.replace(" ", "").replace("-", "")

    if search_type == "name":
        return [p for p in all_patients if query_stripped.lower() in p.get("name", "").lower()]
    elif search_type == "id":
        # EXACT match by patient_number (1=Hamda, 2=Ali, 3=Fatima, 4=Usman)
        return [
            p for p in all_patients
            if str(p.get("patient_number", "")) == query_stripped
        ]
    elif search_type == "phone":
        return [
            p for p in all_patients
            if query_nospace in p.get("phone", "").replace(" ", "").replace("-", "")
        ]
    return []

def create_patient(name: str, email: str, phone: str,
                   date_of_birth: str, location: str,
                   medical_history_summary: Optional[str] = None) -> dict:
    all_patients = get_ref("patients").get() or {}
    max_number = max((p.get("patient_number", 0) for p in all_patients.values()), default=0)

    patient_id = str(uuid.uuid4())
    patient_data = {
        "name": name,
        "email": email,
        "phone": phone,
        "date_of_birth": date_of_birth,
        "location": location,
        "medical_history_summary": medical_history_summary,
        "total_visits": 0,
        "last_visit": None,
        "is_active": True,
        "patient_number": max_number + 1,
    }
    get_ref(f"patients/{patient_id}").set(patient_data)
    patient_data["id"] = patient_id
    return patient_data