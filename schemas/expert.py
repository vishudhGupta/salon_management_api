from pydantic import BaseModel
from typing import List, Optional
import re
import random
import string

class ExpertBase(BaseModel):
    name: str
    phone: str
    address: str
    salon_id: str
    specialization: Optional[str] = None
    experties: Optional[List[str]] = None

class ExpertCreate(ExpertBase):
    pass

class Expert(ExpertBase):
    expert_id: str

    class Config:
        orm_mode = True

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