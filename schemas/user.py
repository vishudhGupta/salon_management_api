from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr
from typing import List, Optional
import re
import random
import string
from datetime import datetime

class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: str
    email: str
    phone_number: str
    address: str
    password: SecretStr
    type: str = "user"  # Default type is user, can be "shop_owner"
    salon_ids: List[str] = []  # List of salon IDs associated with the user

    def dict(self, **kwargs):
        d = super().dict(**kwargs)
        d["password"] = self.password.get_secret_value()
        return d

class UserCreate(UserBase):
    pass

class UserLogin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    email: str
    password: SecretStr

    def dict(self, **kwargs):
        d = super().dict(**kwargs)
        d["password"] = self.password.get_secret_value()
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
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str
    appointments: List[str] = []
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

def generate_user_id(name: str) -> str:
    # Remove special characters and spaces
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
    # Take first 4 characters
    prefix = clean_name[:4]
    # Add timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}{timestamp}" 