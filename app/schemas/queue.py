from pydantic import BaseModel
from typing import Optional

class QueueCreate(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_time: str  # ISO format

class QueueStatusResponse(BaseModel):
    success: bool
    has_active_queue: bool
    queue_data: Optional[dict] = None