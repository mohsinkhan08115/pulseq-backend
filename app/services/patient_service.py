from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.models import Doctor, Patient, doctor_patient

def has_doctor_access(db: Session, doctor_id: int, patient_id: int) -> bool:
    result = db.execute(
        doctor_patient.select().where(
            doctor_patient.c.doctor_id == doctor_id,
            doctor_patient.c.patient_id == patient_id
        )
    ).first()
    return result is not None

def link_doctor_to_patient(db: Session, doctor_id: int, patient_id: int):
    if not has_doctor_access(db, doctor_id, patient_id):
        db.execute(
            doctor_patient.insert().values(
                doctor_id=doctor_id, patient_id=patient_id
            )
        )
        db.commit()

def search_patients(
    db: Session, query: str, search_type: str, doctor_id: int
) -> List[Patient]:
    base = (
        db.query(Patient)
        .join(doctor_patient, Patient.id == doctor_patient.c.patient_id)
        .filter(doctor_patient.c.doctor_id == doctor_id)
        .filter(Patient.is_active == True)
    )
    if search_type == "name":
        return base.filter(Patient.name.ilike(f"%{query}%")).all()
    elif search_type == "id":
        try:
            return base.filter(Patient.id == int(query)).all()
        except ValueError:
            return []
    elif search_type == "phone":
        return base.filter(Patient.phone.contains(query)).all()
    return []

def get_all_doctor_patients(db: Session, doctor_id: int) -> List[Patient]:
    return (
        db.query(Patient)
        .join(doctor_patient, Patient.id == doctor_patient.c.patient_id)
        .filter(doctor_patient.c.doctor_id == doctor_id)
        .filter(Patient.is_active == True)
        .all()
    )

def get_patient_by_id(db: Session, patient_id: int) -> Optional[Patient]:
    return db.query(Patient).filter(
        Patient.id == patient_id, Patient.is_active == True
    ).first()

def create_patient(
    db: Session, name: str, email: str, phone: str,
    date_of_birth: str, location: str,
    medical_history_summary: Optional[str] = None
) -> Patient:
    patient = Patient(
        name=name, email=email, phone=phone,
        date_of_birth=date_of_birth, location=location,
        medical_history_summary=medical_history_summary,
        total_visits=0,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient