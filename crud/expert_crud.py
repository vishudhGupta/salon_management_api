from typing import List, Optional
from schemas.expert import Expert, ExpertCreate
from config.database import Database
import re
import random
import string

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

async def create_expert(expert: ExpertCreate) -> Expert:
    db = Database()
    expert_id = generate_expert_id(expert.name)
    
    expert_dict = expert.dict()
    expert_dict["expert_id"] = expert_id
    
    # Insert expert into database
    await db.experts.insert_one(expert_dict)
    
    # Update salon's experts array
    await db.salons.update_one(
        {"salon_id": expert.salon_id},
        {"$addToSet": {"experts": expert_id}}
    )
    
    return Expert(**expert_dict)

async def get_expert(expert_id: str) -> Optional[Expert]:
    db = Database()
    expert = await db.experts.find_one({"expert_id": expert_id})
    return Expert(**expert) if expert else None

async def get_salon_experts(salon_id: str) -> List[Expert]:
    db = Database()
    experts = await db.experts.find({"salon_id": salon_id}).to_list(length=None)
    return [Expert(**expert) for expert in experts]

async def update_expert(expert_id: str, expert: ExpertCreate) -> Optional[Expert]:
    db = Database()
    expert_dict = expert.dict()
    
    # If salon_id is being changed, update both salons
    old_expert = await db.experts.find_one({"expert_id": expert_id})
    if old_expert and old_expert.get("salon_id") != expert.salon_id:
        # Remove from old salon
        await db.salons.update_one(
            {"salon_id": old_expert["salon_id"]},
            {"$pull": {"experts": expert_id}}
        )
        # Add to new salon
        await db.salons.update_one(
            {"salon_id": expert.salon_id},
            {"$addToSet": {"experts": expert_id}}
        )
    
    result = await db.experts.update_one(
        {"expert_id": expert_id},
        {"$set": expert_dict}
    )
    
    if result.modified_count:
        return await get_expert(expert_id)
    return None

async def delete_expert(expert_id: str) -> bool:
    db = Database()
    expert = await db.experts.find_one({"expert_id": expert_id})
    if expert:
        # Remove from salon's experts array
        await db.salons.update_one(
            {"salon_id": expert["salon_id"]},
            {"$pull": {"experts": expert_id}}
        )
        # Delete expert
        result = await db.experts.delete_one({"expert_id": expert_id})
        return result.deleted_count > 0
    return False

async def get_all_experts() -> List[Expert]:
    db = Database()
    experts = await db.experts.find().to_list(length=None)
    return [Expert(**expert) for expert in experts]

async def get_experts_by_expertise(expertise: str) -> List[Expert]:
    db = Database.get_db()
    experts = await db.experts.find({"expertise": expertise}).to_list(length=None)
    return [Expert(**expert) for expert in experts]

async def get_experts_by_service_and_salon(service_id: str, salon_id: str) -> List[Expert]:
    db = Database.get_db()
    # Find experts who work at the salon and have the required expertise
    service = await db.services.find_one({"service_id": service_id})
    if not service:
        return []
    
    experts = await db.experts.find({
        "salon_id": salon_id,
        "expertise": service["expertise"]
    }).to_list(length=None)
    return [Expert(**expert) for expert in experts] 