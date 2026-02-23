from sqlalchemy import (
    Column, Integer, String, Boolean,
    DateTime, Text, ForeignKey, Table, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# ── Many-to-many: Doctor ↔ Patient ──────────────────────────
doctor_patient = Table(
    "doctor_patient",
    Base.metadata,
    Column("doctor_id", Integer, ForeignKey("doctors.id"), primary_key=True),
    Column("patient_id", Integer, ForeignKey("patients.id"), primary_key=True),
)


class Doctor(Base):
    __tablename__ = "doctors"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(100), nullable=False)
    email          = Column(String(255), unique=True, index=True, nullable=False)
    phone          = Column(String(20),  unique=True, index=True, nullable=False)
    specialization = Column(String(100), nullable=False)
    hospital       = Column(String(200), nullable=False)
    hashed_password= Column(String(255), nullable=False)
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships
    patients        = relationship("Patient",       secondary=doctor_patient, back_populates="doctors")
    medical_records = relationship("MedicalRecord", back_populates="doctor")
    queue_entries   = relationship("QueueEntry",    back_populates="doctor")


class Patient(Base):
    __tablename__ = "patients"

    id                      = Column(Integer, primary_key=True, index=True)
    name                    = Column(String(100), nullable=False)
    email                   = Column(String(255), unique=True, index=True, nullable=False)
    phone                   = Column(String(20),  unique=True, index=True, nullable=False)
    date_of_birth           = Column(String(10),  nullable=False)   # YYYY-MM-DD
    location                = Column(String(200), nullable=False)
    medical_history_summary = Column(Text, nullable=True)
    total_visits            = Column(Integer, default=0)
    last_visit              = Column(String(10), nullable=True)      # YYYY-MM-DD
    is_active               = Column(Boolean, default=True)
    created_at              = Column(DateTime(timezone=True), server_default=func.now())
    updated_at              = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships
    doctors         = relationship("Doctor",        secondary=doctor_patient, back_populates="patients")
    medical_records = relationship("MedicalRecord", back_populates="patient")
    queue_entries   = relationship("QueueEntry",    back_populates="patient")


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id            = Column(Integer, primary_key=True, index=True)
    patient_id    = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id     = Column(Integer, ForeignKey("doctors.id"),  nullable=False)
    diagnosis     = Column(String(500), nullable=False)
    visit_date    = Column(String(10),  nullable=False)   # YYYY-MM-DD
    symptoms      = Column(JSON, default=list)             # ["Fever", ...]
    prescription  = Column(Text, nullable=False)
    notes         = Column(Text, nullable=False)
    follow_up_date= Column(String(10), nullable=True)
    vital_signs   = Column(JSON, nullable=True)            # {"temperature": "101°F", ...}
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships
    patient = relationship("Patient", back_populates="medical_records")
    doctor  = relationship("Doctor",  back_populates="medical_records")


class QueueEntry(Base):
    __tablename__ = "queue_entries"

    id                      = Column(Integer, primary_key=True, index=True)
    token_number            = Column(Integer, nullable=False)
    patient_id              = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id               = Column(Integer, ForeignKey("doctors.id"),  nullable=False)
    appointment_time        = Column(DateTime(timezone=True), nullable=False)
    status                  = Column(String(20), default="confirmed")
    # confirmed → waiting → serving → completed
    check_in_time           = Column(DateTime(timezone=True), nullable=True)
    consultation_start_time = Column(DateTime(timezone=True), nullable=True)
    consultation_end_time   = Column(DateTime(timezone=True), nullable=True)
    actual_duration         = Column(Integer, nullable=True)   # minutes
    notes                   = Column(Text, nullable=True)
    created_at              = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    patient = relationship("Patient", back_populates="queue_entries")
    doctor  = relationship("Doctor",  back_populates="queue_entries")