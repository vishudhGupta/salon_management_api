from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Union
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
    address: str
    name: str
    phone_number: str

class SalonCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: str
    address: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    services: List[str] = []
    experts: List[str] = []
    appointments: List[str] = []
    ratings: Union[List[float], float] = 0.0
    ratings_list: List[dict] = []
    average_rating: float = 0.0
    total_ratings: int = 0

class Salon(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    salon_id: str
    name: str
    address: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    services: List[str] = []
    experts: List[str] = []
    appointments: List[str] = []
    ratings: Union[List[float], float] = 0.0
    ratings_list: List[dict] = []
    average_rating: float = 0.0
    total_ratings: int = 0
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    def __init__(self, **data):
        # Convert float ratings to list if needed
        if isinstance(data.get('ratings'), float):
            data['ratings'] = [data['ratings']] if data['ratings'] != 0.0 else []
        super().__init__(**data)

def generate_salon_id(name: str) -> str:
    clean_name = ''.join(filter(str.isalnum, name.upper()))
    base = clean_name[:3].ljust(3, 'X')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"SL{base}{random_part}"
