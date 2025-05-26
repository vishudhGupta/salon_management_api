from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime,time

class BasicUser(BaseModel):
    user_id: str
    name: str
    phone_number: str

class BasicService(BaseModel):
    service_id: str
    name: str
    cost: float
    duration: int

class BasicExpert(BaseModel):
    expert_id: str
    name: str
    phone: Optional[str]

class AppointmentEntry(BaseModel):
    appointment_id: str
    appointment_date: datetime
    appointment_time: time
    status: str
    user: BasicUser
    service: BasicService
    expert: BasicExpert

class SalonDashboard(BaseModel):
    salon_id: str
    name: str
    address: str
    services: List[BasicService]
    experts: List[BasicExpert]
    appointments: List[AppointmentEntry]
    ratings: float = 0.0
    total_reviews: int = 0
