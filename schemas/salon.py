from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional, Union, Dict
import re
import random
import string
from datetime import datetime, time
from bson import ObjectId

class TimeSlot(BaseModel):
    start_time: time
    end_time: time
    is_available: bool = True

class BreakTime(BaseModel):
    start_time: time
    end_time: time

class Rating(BaseModel):
    user_id: str
    rating: float = Field(ge=1, le=5)  # Rating between 1 and 5
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True  # Updated from orm_mode for Pydantic v2

class SalonBase(BaseModel):
    name: str
    address: str
    phone: str
    description: Optional[str] = None
    services: List[str] = []
    experts: List[str] = []
    appointments: List[str] = []
    ratings: List[Rating] = []  # List of Rating objects
    average_rating: float = 0.0
    total_ratings: int = 0

class SalonCreate(SalonBase):
    pass

class SalonUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    services: Optional[List[str]] = None
    experts: Optional[List[str]] = None
    appointments: Optional[List[str]] = None
    ratings: Optional[List[Rating]] = None

class Salon(SalonBase):
    salon_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True  # Updated from orm_mode for Pydantic v2

    @property
    def calculate_average_rating(self) -> float:
        """Calculate average rating from the ratings list"""
        if not self.ratings:
            return 0.0
        return sum(r.rating for r in self.ratings) / len(self.ratings)

    @property
    def calculate_total_ratings(self) -> int:
        """Calculate total number of ratings"""
        return len(self.ratings)

class Appointment(BaseModel):
    appointment_id: str
    user_id: str
    salon_id: str
    service_id: str
    expert_id: str
    appointment_date: datetime
    appointment_time: str
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ExpertAvailability(BaseModel):
    expert_id: str
    salon_id: str
    is_available: bool = True
    availability: Dict[str, List[bool]] = {
        "0": [True] * 13,  # Sunday
        "1": [True] * 13,  # Monday
        "2": [True] * 13,  # Tuesday
        "3": [True] * 13,  # Wednesday
        "4": [True] * 13,  # Thursday
        "5": [True] * 13,  # Friday
        "6": [True] * 13   # Saturday
    }

def generate_salon_id(name: str) -> str:
    """Generate a unique salon ID based on the salon name"""
    # Remove special characters and spaces, convert to uppercase
    clean_name = ''.join(c for c in name if c.isalnum()).upper()
    # Take first 3 characters
    prefix = clean_name[:3] if len(clean_name) >= 3 else clean_name.ljust(3, 'X')
    # Add random 3 digits
    import random
    suffix = ''.join(random.choices('0123456789', k=3))
    return f"SALON{prefix}{suffix}"
