from typing import List, Optional
from schemas.user import UserCreate, User, generate_user_id, UserLogin
from config.database import Database
from pydantic import SecretStr
from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_user(user: UserCreate) -> User:
    db = Database()
    user_id = generate_user_id(user.name)
    user_dict = user.dict()
    
    # Hash the password before storing
    password = user_dict["password"]
    user_dict["password"] = pwd_context.hash(password)
    user_dict["user_id"] = user_id
    user_dict["appointments"] = []
    
    await db.users.insert_one(user_dict)
    # Convert password back to SecretStr for response
    user_dict["password"] = SecretStr(password)
    return User(**user_dict)

async def get_user(user_id: str) -> Optional[User]:
    db = Database()
    user = await db.users.find_one({"user_id": user_id})
    if user:
        # Convert the stored password string back to SecretStr
        user['password'] = SecretStr(user['password'])
        return User(**user)
    return None

async def get_user_by_phone(phone_number: str) -> Optional[User]:
    db = Database()
    user = await db.users.find_one({"phone_number": phone_number})
    if user:
        # Convert the stored password string back to SecretStr
        user['password'] = SecretStr(user['password'])
        return User(**user)
    return None

async def get_user_by_email(email: str) -> Optional[User]:
    db = Database()
    user = await db.users.find_one({"email": email})
    if user:
        # Convert the stored password string back to SecretStr
        user['password'] = SecretStr(user['password'])
        return User(**user)
    return None

async def update_user(user_id: str, user_data: dict) -> Optional[User]:
    db = Database()
    update_result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": user_data}
    )
    if update_result.modified_count:
        return await get_user(user_id)
    return None

async def get_all_users() -> List[User]:
    db = Database()
    users = await db.users.find().to_list(length=None)
    return [User(**{**user, 'password': SecretStr(user['password'])}) for user in users]

async def fetch_user_dashboard(user_id: str):
    db = Database()

    # Fetch the user
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.pop("password", None)

    # Expand all appointments
    appointment_ids = user.get("appointments", [])
    appointments_raw = await db.appointments.find({
        "appointment_id": {"$in": appointment_ids}
    }).to_list(length=None)

    enriched_appointments = []
    for appt in appointments_raw:
        expert = await db.experts.find_one({"expert_id": appt["expert_id"]})
        salon = await db.salons.find_one({"salon_id": appt["salon_id"]})
        service = await db.services.find_one({"service_id": appt["service_id"]})

        appt["expert"] = expert
        appt["salon"] = salon
        appt["service"] = service

        # Remove internal Mongo ID
        appt.pop("_id", None)
        enriched_appointments.append(appt)

    user["appointments"] = enriched_appointments
    return user

async def login_user(login_data: UserLogin) -> Optional[User]:
    db = Database()
    user = await db.users.find_one({"email": login_data.email})
    if not user:
        return None
        
    # Get the stored password
    stored_password = user["password"]
    input_password = login_data.password.get_secret_value()
    
    # Check if the stored password is already hashed
    if isinstance(stored_password, str) and stored_password.startswith("$2b$"):
        # Verify hashed password
        if not pwd_context.verify(input_password, stored_password):
            return None
    else:
        # Direct comparison for unhashed passwords (temporary during migration)
        if input_password != stored_password:
            return None
        # Hash the password for future use
        hashed_password = pwd_context.hash(input_password)
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"password": hashed_password}}
        )
    
    # Convert the stored password back to SecretStr for the response
    user['password'] = SecretStr(stored_password)
    return User(**user)