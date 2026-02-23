from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.models import MedicalRecord, Patient
from app.services.patient_service import has_doctor_access, link_doctor_to_patient

def get_medical_records(
    db: Session, patient_id: int, doctor_id: int
) -> List[MedicalRecord]:
    if not has_doctor_access(db, doctor_id, patient_id):
        return []
    return (
        db.query(MedicalRecord)
        .options(
            joinedload(MedicalRecord.patient),
            joinedload(MedicalRecord.doctor)
        )
        .filter(MedicalRecord.patient_id == patient_id)
        .order_by(MedicalRecord.visit_date.desc())
        .all()
    )

def create_medical_record(
    db: Session, doctor_id: int, patient_id: int,
    diagnosis: str, visit_date: str, symptoms: List[str],
    prescription: str, notes: str,
    follow_up_date: Optional[str] = None,
    vital_signs: Optional[dict] = None,
) -> MedicalRecord:
    record = MedicalRecord(
        patient_id=patient_id, doctor_id=doctor_id,
        diagnosis=diagnosis, visit_date=visit_date,
        symptoms=symptoms, prescription=prescription,
        notes=notes, follow_up_date=follow_up_date,
        vital_signs=vital_signs,
    )
    db.add(record)

    # Update patient visit stats
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient:
        patient.total_visits = (patient.total_visits or 0) + 1
        patient.last_visit = visit_date

    db.commit()
    db.refresh(record)

    # Ensure doctor-patient link exists
    link_doctor_to_patient(db, doctor_id, patient_id)
    return record

def update_medical_record(
    db: Session, record_id: int, doctor_id: int, **kwargs
) -> Optional[MedicalRecord]:
    record = db.query(MedicalRecord).filter(
        MedicalRecord.id == record_id,
        MedicalRecord.doctor_id == doctor_id
    ).first()
    if not record:
        return None
    for key, value in kwargs.items():
        if value is not None:
            setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record