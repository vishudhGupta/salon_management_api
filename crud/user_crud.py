from typing import List, Optional
from schemas.user import UserCreate, User, generate_user_id, UserLogin, UserBase
from schemas.user_dashboard import UserDashboard
from config.database import Database
from pydantic import SecretStr, EmailStr
from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from datetime import datetime

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
    validated_users = []
    
    for user in users:
        try:
            # Create a temporary UserBase instance to validate email
            temp_user = UserBase(
                name=user["name"],
                email=user["email"],
                phone_number=user["phone_number"],
                address=user["address"],
                password=SecretStr("dummy")  # Dummy password for validation
            )
            # If validation succeeds, use the original user data
            validated_users.append(User(**{**user, 'password': SecretStr(user['password'])}))
        except ValueError:
            # If email is invalid, create a placeholder email
            user["email"] = f"{user['user_id']}@placeholder.com"
            # Update the user's email in the database
            await db.users.update_one(
                {"user_id": user["user_id"]},
                {"$set": {"email": user["email"]}}
            )
            validated_users.append(User(**{**user, 'password': SecretStr(user['password'])}))
    
    return validated_users

async def fetch_user_dashboard(user_id: str) -> UserDashboard:
    db = Database()

    # Fetch the user
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.pop("password", None)

    # Validate and format email
    try:
        # Create a temporary UserBase instance to validate email
        temp_user = UserBase(
            name=user["name"],
            email=user["email"],
            phone_number=user["phone_number"],
            address=user["address"],
            password=SecretStr("dummy")  # Dummy password for validation
        )
        email = temp_user.email
    except ValueError:
        # If email is invalid, use a placeholder email
        email = f"{user['user_id']}@placeholder.com"
        # Update the user's email in the database
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"email": email}}
        )

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

        if expert and salon and service:
            enriched_appointments.append({
                "appointment_id": appt["appointment_id"],
                "appointment_date": appt["appointment_date"],
                "appointment_time": appt["appointment_time"],
                "status": appt["status"],
                "expert_confirmed": appt.get("expert_confirmed", False),
                "notes": appt.get("notes"),
                "created_at": appt.get("created_at", datetime.now()),
                "salon": {
                    "salon_id": salon["salon_id"],
                    "name": salon["name"],
                    "address": salon.get("address")
                },
                "expert": {
                    "expert_id": expert["expert_id"],
                    "name": expert["name"],
                    "phone": expert.get("phone"),
                    "address": expert.get("address")
                },
                "service": {
                    "service_id": service["service_id"],
                    "name": service["name"],
                    "description": service.get("description"),
                    "cost": service["cost"],
                    "duration": service["duration"]
                }
            })

    # Create UserDashboard instance
    dashboard_data = UserDashboard(
        user_id=user["user_id"],
        name=user["name"],
        email=email,  # Use the validated email
        phone_number=user["phone_number"],
        address=user["address"],
        appointments=enriched_appointments,
        favorite_salons=user.get("favorite_salons", []),
        favorite_services=user.get("favorite_services", [])
    )

    return dashboard_data

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