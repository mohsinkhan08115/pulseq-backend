from typing import Optional
from sqlalchemy.orm import Session
from app.models.models import Doctor
from app.core.security import verify_password, get_password_hash, create_access_token

def authenticate_doctor(
    db: Session,
    phone: Optional[str],
    email: Optional[str],
    password: str
) -> Optional[Doctor]:
    doctor = None
    if email:
        doctor = db.query(Doctor).filter(
            Doctor.email == email, Doctor.is_active == True
        ).first()
    elif phone:
        doctor = db.query(Doctor).filter(
            Doctor.phone == phone, Doctor.is_active == True
        ).first()
    if not doctor:
        return None
    if not verify_password(password, doctor.hashed_password):
        return None
    return doctor

def register_doctor(
    db: Session, name: str, email: str, phone: str,
    specialization: str, hospital: str, password: str
) -> Doctor:
    doctor = Doctor(
        name=name, email=email, phone=phone,
        specialization=specialization, hospital=hospital,
        hashed_password=get_password_hash(password),
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor

def create_token_for_doctor(doctor_id: int) -> str:
    return create_access_token(data={"sub": str(doctor_id)})

def get_doctor_by_id(db: Session, doctor_id: int) -> Optional[Doctor]:
    return db.query(Doctor).filter(
        Doctor.id == doctor_id, Doctor.is_active == True
    ).first()