from fastapi import APIRouter, HTTPException, status
from app.core.database import get_ref
from app.schemas.auth import LoginRequest, RegisterDoctorRequest, Token
from app.services.auth_service import (
    authenticate_doctor,
    register_doctor,
    create_token_for_doctor,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _doctor_to_dict(doctor: dict) -> dict:
    return {
        "id": doctor["id"],
        "name": doctor["name"],
        "email": doctor["email"],
        "phone": doctor["phone"],
        "specialization": doctor["specialization"],
        "hospital": doctor["hospital"],
    }


@router.post("/login", response_model=Token)
def login(request: LoginRequest):
    if not request.email and not request.phone:
        raise HTTPException(status_code=400, detail="Provide email or phone")

    doctor = authenticate_doctor(
        request.phone,
        request.email,
        request.password
    )

    if not doctor:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(
        access_token=create_token_for_doctor(doctor["id"]),
        token_type="bearer",
        doctor=_doctor_to_dict(doctor),
    )


@router.post("/register", response_model=Token, status_code=201)
def register(request: RegisterDoctorRequest):
    doctors_ref = get_ref("doctors")
    doctors = doctors_ref.get() or {}

    # Check duplicate email or phone
    for doc_id, doctor in doctors.items():
        if doctor.get("email") == request.email:
            raise HTTPException(status_code=400, detail="Email already registered")
        if doctor.get("phone") == request.phone:
            raise HTTPException(status_code=400, detail="Phone already registered")

    doctor = register_doctor(
        name=request.name,
        email=request.email,
        phone=request.phone,
        specialization=request.specialization,
        hospital=request.hospital,
        password=request.password,
    )

    return Token(
        access_token=create_token_for_doctor(doctor["id"]),
        token_type="bearer",
        doctor=_doctor_to_dict(doctor),
    )