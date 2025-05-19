from pydantic import BaseModel, Field
from typing import List, Optional
import re
import random
import string
from datetime import datetime

class Rating(BaseModel):
    user_id: str
    rating: float = Field(ge=1, le=5)  # Rating between 1 and 5
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Appointment(BaseModel):
    appointment_id: str
    user_id: str
    service_id: str
    expert_id: str
    date: datetime
    status: str  # pending, confirmed, completed, cancelled
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SalonBase(BaseModel):
    shop_owner_id: str
    address: str
    name: str
    phone_number: str

class SalonCreate(SalonBase):
    pass

class Salon(SalonBase):
    salon_id: str
    services: List[str] = []  # This will store service IDs
    experts: List[str] = []   # This will store expert IDs
    appointments: List[Appointment] = []
    ratings: List[Rating] = []
    average_rating: float = 0.0
    total_ratings: int = 0

    class Config:
        orm_mode = True

def generate_salon_id(shop_owner_id: str) -> str:
    # Take first 3 characters of the shop_owner_id
    owner_part = shop_owner_id[:3]
    
    # Generate 4 random alphanumeric characters
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # Combine to create 7-character unique ID
    salon_id = f"SL{owner_part}{random_part}"
    
    return salon_id 