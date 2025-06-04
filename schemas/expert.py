from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import re
import random
import string
from datetime import datetime, time
from schemas.salon import TimeSlot

class ExpertBase(BaseModel):
    name: str
    phone: str
    address: str
    salon_id: str
    specialization: Optional[str] = None
    experties: Optional[List[str]] = None

class ExpertCreate(ExpertBase):
    pass

class ExpertUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    specialization: Optional[str] = None
    experties: Optional[List[str]] = None
    availability: Optional[List[bool]] = None

class Expert(ExpertBase):
    expert_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True

class ExpertAvailability(BaseModel):
    expert_id: str
    salon_id: str
    is_available: bool = True
    availability: Dict[str, List[bool]] = Field(
        default_factory=lambda: {
            str(i): [True] * 13 for i in range(7)
        },
        description="Map weekday index ('0'=Sunday) to 13 hourly slots (9AM–9PM)"
    )

def generate_expert_id(name: str) -> str:
    # Remove special characters and spaces from name
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', name)
    
    # Take first 3 characters of the name (or pad with 'X' if shorter)
    name_part = clean_name[:3].upper().ljust(3, 'X')
    
    # Generate 4 random alphanumeric characters
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # Combine to create 7-character unique ID
    expert_id = f"EX{name_part}{random_part}"
    
    return expert_id 