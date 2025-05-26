from pydantic import BaseModel, EmailStr, Field, SecretStr
from typing import List, Optional
import re
import random
import string

class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone_number: str
    address: str
    password: SecretStr  # Making password required again
    type: str = "user"  # Default type is user, can be "shop_owner"
    salon_ids: List[str] = []  # List of salon IDs associated with the user

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        # Convert SecretStr to string for database storage
        if isinstance(d.get('password'), SecretStr):
            d['password'] = d['password'].get_secret_value()
        return d

class UserCreate(UserBase):
    pass

class UserLogin(BaseModel):
    phone_number: str
    password: SecretStr

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        if isinstance(d.get('password'), SecretStr): 
            d['password'] = d['password'].get_secret_value()
        return d



class SalonDashboard(BaseModel):
    salon_id: str
    name: str
    address: str
    services: List[dict] = []
    experts: List[dict] = []
    appointments: List[dict] = []
    ratings: float = 0.0
    total_reviews: int = 0

class User(UserBase):
    user_id: str
    appointments: List[str] = []  # This will store appointment IDs

    class Config:
        orm_mode = True

def generate_user_id(name: str) -> str:
    # Remove special characters and spaces from name
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', name)
    
    # Take first 3 characters of the name (or pad with 'X' if shorter)
    name_part = clean_name[:3].upper().ljust(3, 'X')
    
    # Generate 4 random alphanumeric characters
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # Combine to create 7-character unique ID
    user_id = f"{name_part}{random_part}"
    
    return user_id 