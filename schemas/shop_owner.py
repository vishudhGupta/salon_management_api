from pydantic import BaseModel, EmailStr, SecretStr
from typing import List
import re
import random
import string

class ShopOwnerBase(BaseModel):
    user_id: str  # Reference to the user who owns the shop
    email: EmailStr
    phone_number: str
    password: SecretStr

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        # Convert SecretStr to string for database storage
        if isinstance(d.get('password'), SecretStr):
            d['password'] = d['password'].get_secret_value()
        return d

class ShopOwnerCreate(ShopOwnerBase):
    pass

class ShopOwner(ShopOwnerBase):
    shop_owner_id: str
    salons: List[str] = []  # This will store salon IDs

    class Config:
        orm_mode = True

def generate_shop_owner_id(user_id: str) -> str:
    # Take first 3 characters of the user_id
    user_part = user_id[:3]
    
    # Generate 4 random alphanumeric characters
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # Combine to create 7-character unique ID
    shop_owner_id = f"SO{user_part}{random_part}"
    
    return shop_owner_id 