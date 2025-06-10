from pydantic import BaseModel, Field
from datetime import datetime
import re
import random
import string
from typing import Optional, Dict

class UserDetails(BaseModel):
    user_id: str
    name: str
    email: str
    phone_number: str
    address: str

class ExpertDetails(BaseModel):
    expert_id: str
    name: str
    phone: str
    address: str
    specialization: Optional[str] = None
    experties: Optional[list[str]] = None

class ServiceDetails(BaseModel):
    service_id: str
    name: str
    description: Optional[str] = None
    cost: float
    duration: int

class AppointmentBase(BaseModel):
    salon_id: str
    user: UserDetails
    service: ServiceDetails
    expert: Optional[ExpertDetails] = Field(None, description="Details of the expert selected for the appointment")
    appointment_date: datetime
    appointment_time: str = Field(..., description="Format: HH:MM in 24-hour format")
    notes: Optional[str] = Field(None, description="Any additional notes for the appointment")

class AppointmentCreate(AppointmentBase):
    pass

class Appointment(AppointmentBase):
    appointment_id: str
    status: str = "pending"  # pending, confirmed, completed, cancelled
    created_at: datetime = datetime.utcnow()
    expert_confirmed: bool = Field(False, description="Whether the expert has confirmed the appointment")

    class Config:
        orm_mode = True

def generate_appointment_id(salon_id: str, user_id: str) -> str:
    # Take first 2 characters of both salon_id and user_id
    salon_part = salon_id[:2]
    user_part = user_id[:2]
    
    # Generate 3 random alphanumeric characters
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    
    # Combine to create 7-character unique ID
    appointment_id = f"AP{salon_part}{user_part}{random_part}"
    
    return appointment_id 