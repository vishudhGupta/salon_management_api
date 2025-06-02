from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional, Union, Dict
import re
import random
import string
from datetime import datetime, time
from bson import ObjectId

class Rating(BaseModel):
    user_id: str
    rating: float = Field(ge=1, le=5)  # Rating between 1 and 5
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Appointment(BaseModel):
    appointment_id: str
    user_id: str
    salon_id: str
    service_id: str
    expert_id: str
    appointment_date: datetime
    appointment_time: time
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SalonBase(BaseModel):
    name: str
    address: str
    phone: str
    description: Optional[str] = None
    average_rating: float = 0.0
    total_ratings: int = 0

class TimeSlot(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            time: lambda v: v.strftime("%H:%M")
        }
    )
    start_time: time
    end_time: time

    @field_validator('start_time', 'end_time')
    @classmethod
    def remove_timezone(cls, v: time) -> time:
        if v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v

class BreakTime(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            time: lambda v: v.strftime("%H:%M")
        }
    )
    start_time: time
    end_time: time

    @field_validator('start_time', 'end_time')
    @classmethod
    def remove_timezone(cls, v: time) -> time:
        if v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v

class DayWorkingHours(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            time: lambda v: v.strftime("%H:%M")
        }
    )
    day_of_week: int  # 0-6 (Monday-Sunday)
    time_slots: Optional[List[TimeSlot]] = None  # Optional, if None means available all day
    break_time: Optional[List[BreakTime]] = None

    def is_available(self, check_time: time) -> bool:
        """Check if the given time is available on this day"""
        # If no time slots defined, day is fully available except for break times
        if not self.time_slots:
            # Check if time falls in any break time
            if self.break_time:
                for break_slot in self.break_time:
                    if break_slot.start_time <= check_time <= break_slot.end_time:
                        return False
            return True
        
        # Check if time falls in any available time slot
        for slot in self.time_slots:
            if slot.is_available and slot.start_time <= check_time <= slot.end_time:
                # Check if time falls in any break time
                if self.break_time:
                    for break_slot in self.break_time:
                        if break_slot.start_time <= check_time <= break_slot.end_time:
                            return False
                return True
        return False

class SalonWorkingHours(BaseModel):
    salon_id: str
    is_available: List[bool] = Field(
        default_factory=lambda: [True] * 7,
        description="Array of 7 booleans representing availability for each day of the week (Monday to Sunday)"
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ExpertWorkingHours(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            time: lambda v: v.strftime("%H:%M")
        }
    )
    expert_id: str
    break_days: List[int] = []  # List of days (0-6) when expert is not available
    break_times: List[BreakTime] = []  # List of break times for each day
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def is_available(self, day_of_week: int, check_time: time) -> bool:
        # Check if the day is a break day
        if day_of_week in self.break_days:
            return False
        
        # Check if the time falls within any break time
        for break_time in self.break_times:
            if break_time.start_time <= check_time <= break_time.end_time:
                return False
        
        # If no restrictions found, expert is available
        return True

class Salon(SalonBase):
    salon_id: str
    services: List[str] = []
    experts: List[str] = []
    appointments: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    working_hours: Optional[SalonWorkingHours] = None
    expert_working_hours: Dict[str, ExpertWorkingHours] = {}

    class Config:
        orm_mode = True

class SalonCreate(SalonBase):
    pass

class SalonUpdate(SalonBase):
    pass

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
