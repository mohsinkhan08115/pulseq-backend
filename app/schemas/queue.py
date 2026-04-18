from pydantic import BaseModel
from typing import Optional, List


class QueueCreate(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_time: str  # ISO format


class QueueStatusResponse(BaseModel):
    success: bool
    has_active_queue: bool
    queue_data: Optional[dict] = None


class BookTokenRequest(BaseModel):
    patient_id: str
    doctor_id: str


class MultiDoctorBookRequest(BaseModel):
    patient_id: str
    doctor_ids: List[str]  # list of doctors in order
    slot_duration_minutes: int = 15


class AIPrediction(BaseModel):
    estimated_minutes: int
    estimated_time: str
    consultation_duration: int
    patients_ahead: int
    confidence_percent: int
    peak_hour: bool


class TokenBookingResult(BaseModel):
    success: bool
    already_existed: bool
    message: str
    token_number: int
    booking_type: str
    patient_name: str
    doctor_name: str
    status: str
    show_queue_status: bool
    ai_prediction: AIPrediction


class MultiDoctorBookingResult(BaseModel):
    success: bool
    total_bookings: int
    bookings: List[dict]
    message: str