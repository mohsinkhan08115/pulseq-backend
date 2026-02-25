from typing import List, Optional
from app.core.database import get_ref
from app.services.patient_service import has_doctor_access, link_doctor_to_patient, get_patient_by_id
import uuid


def get_medical_records(patient_id: str, doctor_id: str) -> List[dict]:
    if not has_doctor_access(doctor_id, patient_id):
        return []
    all_records = get_ref("medical_records").get() or {}
    records = []
    for rec_id, record in all_records.items():
        if record.get("patient_id") == patient_id:
            record["id"] = rec_id
            patient = get_patient_by_id(patient_id)
            doctor = get_ref(f"doctors/{record['doctor_id']}").get() or {}
            record["patient_name"] = patient["name"] if patient else ""
            record["doctor_name"] = doctor.get("name", "")
            records.append(record)
    records.sort(key=lambda x: x.get("visit_date", ""), reverse=True)
    return records


def create_medical_record(doctor_id: str, patient_id: str, diagnosis: str,
                           visit_date: str, symptoms: List[str], prescription: str,
                           notes: str, follow_up_date: Optional[str] = None,
                           vital_signs: Optional[dict] = None) -> dict:
    record_id = str(uuid.uuid4())
    record_data = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "diagnosis": diagnosis,
        "visit_date": visit_date,
        "symptoms": symptoms,
        "prescription": prescription,
        "notes": notes,
        "follow_up_date": follow_up_date,
        "vital_signs": vital_signs,
    }
    get_ref(f"medical_records/{record_id}").set(record_data)

    # Update patient visit stats
    patient = get_patient_by_id(patient_id)
    if patient:
        get_ref(f"patients/{patient_id}").update({
            "total_visits": (patient.get("total_visits") or 0) + 1,
            "last_visit": visit_date,
        })

    link_doctor_to_patient(doctor_id, patient_id)

    record_data["id"] = record_id
    doctor = get_ref(f"doctors/{doctor_id}").get() or {}
    record_data["patient_name"] = patient["name"] if patient else ""
    record_data["doctor_name"] = doctor.get("name", "")
    return record_data


def update_medical_record(record_id: str, doctor_id: str, **kwargs) -> Optional[dict]:
    record = get_ref(f"medical_records/{record_id}").get()
    if not record:
        return None
    if record.get("doctor_id") != doctor_id:
        return None
    updates = {k: v for k, v in kwargs.items() if v is not None}
    if updates:
        get_ref(f"medical_records/{record_id}").update(updates)
    updated = get_ref(f"medical_records/{record_id}").get()
    updated["id"] = record_id
    patient = get_patient_by_id(updated["patient_id"])
    doctor = get_ref(f"doctors/{doctor_id}").get() or {}
    updated["patient_name"] = patient["name"] if patient else ""
    updated["doctor_name"] = doctor.get("name", "")
    return updated