from pydantic import BaseModel, Field
from typing import List, Optional
import re
import random
import string

class ServiceBase(BaseModel):
    name: str
    description: str
    cost: float = Field(gt=0)
    duration: int = Field(gt=0)  # Duration in minutes
    salon_id: str  # Added salon_id field

class ServiceCreate(ServiceBase):
    pass

class Service(ServiceBase):
    service_id: str

    class Config:
        orm_mode = True

def generate_service_id(name: str) -> str:
    # Remove special characters and spaces from name
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', name)
    
    # Take first 3 characters of the name (or pad with 'X' if shorter)
    name_part = clean_name[:3].upper().ljust(3, 'X')
    
    # Generate 4 random alphanumeric characters
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # Combine to create 7-character unique ID
    service_id = f"SV{name_part}{random_part}"
    
    return service_id 