from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime,time

class SalonInfo(BaseModel):
    salon_id: str
    name: str
    address: Optional[str]

class ExpertInfo(BaseModel):
    expert_id: str
    name: str
    phone: Optional[str]
    address: Optional[str]

class ServiceInfo(BaseModel):
    service_id: str
    name: str
    description: Optional[str]
    cost: float
    duration: int

class AppointmentInfo(BaseModel):
    appointment_id: str
    appointment_date: datetime
    appointment_time: time
    status: str
    expert_confirmed: bool
    notes: Optional[str]
    created_at: datetime
    salon: SalonInfo
    expert: ExpertInfo
    service: ServiceInfo

class UserDashboard(BaseModel):
    user_id: str
    name: str
    email: EmailStr
    phone_number: str
    address: str
    appointments: List[AppointmentInfo] = []
    favorite_salons: List[str] = []
    favorite_services: List[str] = []
