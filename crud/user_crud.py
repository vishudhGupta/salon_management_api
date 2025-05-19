from typing import List, Optional
from schemas.user import UserCreate, User, generate_user_id
from config.database import Database
from pydantic import SecretStr

async def create_user(user: UserCreate) -> User:
    db = Database()
    user_id = generate_user_id(user.name)
    user_dict = user.dict()
    user_dict["user_id"] = user_id
    user_dict["appointments"] = []
    
    await db.users.insert_one(user_dict)
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