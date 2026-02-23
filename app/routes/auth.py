from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.auth import LoginRequest, RegisterDoctorRequest, Token
from app.services.auth_service import (
    authenticate_doctor, register_doctor, create_token_for_doctor
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

def _doctor_to_dict(doctor) -> dict:
    return {
        "id": doctor.id,
        "name": doctor.name,
        "email": doctor.email,
        "phone": doctor.phone,
        "specialization": doctor.specialization,
        "hospital": doctor.hospital,
    }

@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email OR phone + password.
    Returns a JWT valid for 24 hours.
    """
    if not request.email and not request.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide email or phone"
        )
    doctor = authenticate_doctor(db, request.phone, request.email, request.password)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(
        access_token=create_token_for_doctor(doctor.id),
        token_type="bearer",
        doctor=_doctor_to_dict(doctor),
    )

@router.post("/register", response_model=Token, status_code=201)
def register(request: RegisterDoctorRequest, db: Session = Depends(get_db)):
    """Register a new doctor account."""
    from app.models.models import Doctor
    if db.query(Doctor).filter(Doctor.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(Doctor).filter(Doctor.phone == request.phone).first():
        raise HTTPException(status_code=400, detail="Phone already registered")

    doctor = register_doctor(
        db, name=request.name, email=request.email,
        phone=request.phone, specialization=request.specialization,
        hospital=request.hospital, password=request.password,
    )
    return Token(
        access_token=create_token_for_doctor(doctor.id),
        token_type="bearer",
        doctor=_doctor_to_dict(doctor),
    )