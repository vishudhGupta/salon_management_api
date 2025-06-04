from typing import List, Optional, Dict, Any,Union
from schemas.expert import (
    Expert, ExpertCreate, ExpertAvailability,
    ExpertUpdate
)
from schemas.salon import Appointment, TimeSlot
from config.database import Database
import re
import random
import string
from datetime import datetime, time, timedelta
import logging
from bson import ObjectId
from fastapi import HTTPException


logger = logging.getLogger(__name__)

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
    availability_doc = {
        "expert_id": expert_id,
        "salon_id": expert.salon_id,
        "is_available": True,
        "availability": {str(i): [True] * 13 for i in range(7)}
    }
    
    # Update salon's experts array
    await db.salons.update_one(
        {"salon_id": expert.salon_id},
        {"$addToSet": {"experts": expert_id}}
    )
    
    return Expert(**expert_dict)

async def get_expert_availability(expert_id: str) -> Optional[ExpertAvailability]:
    """Get availability for an expert"""
    db = Database()
    availability = await db.expert_availability.find_one({"expert_id": expert_id})
    return ExpertAvailability(**availability) if availability else None

async def update_expert_availability(availability: ExpertAvailability) -> ExpertAvailability:
    """Update availability for an expert"""
    db = Database()
    await db.expert_availability.update_one(
        {"expert_id": availability.expert_id},
        {"$set": availability.dict()},
        upsert=True
    )
    return availability





async def get_available_experts(
    salon_id: str, 
    date: datetime, 
    time_slot: Union[TimeSlot, dict], 
    db: Database
) -> List[str]:
    if isinstance(time_slot, dict):
        time_slot = TimeSlot(**time_slot)

    salon = await db.salons.find_one({"salon_id": salon_id})
    if not salon or "experts" not in salon:
        return []

    available_experts = []

    weekday = str(date.weekday())  # '0' = Monday, ..., '6' = Sunday
    hour_index = time_slot.start_time.hour - 9

    for expert_id in salon["experts"]:
        expert = await db.experts.find_one({"expert_id": expert_id})
        if not expert:
            continue

        availability_doc = await db.expert_availability.find_one({"expert_id": expert_id})
        if not availability_doc:
            continue

        availability = availability_doc.get("availability", {})
        day_slots = availability.get(weekday, [True] * 13)

        # Validate slot index
        if hour_index < 0 or hour_index >= len(day_slots) or not day_slots[hour_index]:
            continue

        # Check appointment conflict
        conflict = await db.appointments.find_one({
            "expert_id": expert_id,
            "appointment_date": {
                "$gte": datetime.combine(date, time(0, 0)),
                "$lt": datetime.combine(date, time(23, 59))
            },
            "appointment_time": time_slot.start_time.strftime("%H:%M"),
            "status": {"$in": ["pending", "confirmed"]}
        })

        if not conflict:
            available_experts.append(expert_id)

    return available_experts


async def update_expert(expert_id: str, expert_update: ExpertUpdate) -> Optional[Expert]:
    """Update an expert's information"""
    db = Database()
    
    # Remove None values from update dict
    update_data = {k: v for k, v in expert_update.dict().items() if v is not None}
    if not update_data:
        return None
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.experts.update_one(
        {"expert_id": expert_id},
        {"$set": update_data}
    )
    
    if result.modified_count:
        updated_expert = await db.experts.find_one({"expert_id": expert_id})
        return Expert(**updated_expert) if updated_expert else None
    return None

async def get_expert(expert_id: str) -> Optional[Expert]:
    """Get an expert by ID"""
    db = Database()
    expert = await db.experts.find_one({"expert_id": expert_id})
    return Expert(**expert) if expert else None

async def get_expert_by_salon(salon_id: str, expert_id: str) -> Optional[Expert]:
    """Get a specific expert from a salon"""
    db = Database()
    expert = await db.experts.find_one({
        "salon_id": salon_id,
        "expert_id": expert_id
    })
    return Expert(**expert) if expert else None

async def get_experts_by_salon(salon_id: str) -> List[Expert]:
    """Get all experts for a salon"""
    db = Database()
    experts = await db.experts.find({"salon_id": salon_id}).to_list(length=None)
    return [Expert(**expert) for expert in experts]

async def delete_expert(expert_id: str) -> bool:
    """Delete an expert"""
    db = Database()
    expert = await get_expert(expert_id)
    if not expert:
        return False
    
    # Remove expert from salon's experts array
    await db.salons.update_one(
        {"salon_id": expert.salon_id},
        {"$pull": {"experts": expert_id}}
    )
    
    # Delete expert's availability
    await db.expert_availability.delete_one({"expert_id": expert_id})
    
    # Delete expert
    result = await db.experts.delete_one({"expert_id": expert_id})
    return result.deleted_count > 0

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
        "expertise": service["expertise"],
        "isWorking": False  # Only get experts who are not currently working
    }).to_list(length=None)
    return [Expert(**expert) for expert in experts] 