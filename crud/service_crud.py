from typing import List, Optional
from schemas.service import Service, ServiceCreate
from config.database import Database
import re
import random
import string

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

async def create_service(service: ServiceCreate) -> Service:
    db = Database()
    service_id = generate_service_id(service.name)
    
    service_dict = service.dict()
    service_dict["service_id"] = service_id
    
    # Insert service into database
    await db.services.insert_one(service_dict)
    
    # Update salon's services array
    await db.salons.update_one(
        {"salon_id": service.salon_id},
        {"$addToSet": {"services": service_id}}
    )
    
    return Service(**service_dict)

async def get_service(service_id: str) -> Optional[Service]:
    db = Database()
    service = await db.services.find_one({"service_id": service_id})
    return Service(**service) if service else None

async def get_salon_services(salon_id: str) -> List[Service]:
    db = Database()
    services = await db.services.find({"salon_id": salon_id}).to_list(length=None)
    return [Service(**service) for service in services]

async def update_service(service_id: str, service: ServiceCreate) -> Optional[Service]:
    db = Database()
    service_dict = service.dict()
    
    # If salon_id is being changed, update both salons
    old_service = await db.services.find_one({"service_id": service_id})
    if old_service and old_service.get("salon_id") != service.salon_id:
        # Remove from old salon
        await db.salons.update_one(
            {"salon_id": old_service["salon_id"]},
            {"$pull": {"services": service_id}}
        )
        # Add to new salon
        await db.salons.update_one(
            {"salon_id": service.salon_id},
            {"$addToSet": {"services": service_id}}
        )
    
    result = await db.services.update_one(
        {"service_id": service_id},
        {"$set": service_dict}
    )
    
    if result.modified_count:
        return await get_service(service_id)
    return None

async def delete_service(service_id: str) -> bool:
    db = Database()
    service = await db.services.find_one({"service_id": service_id})
    if service:
        # Remove from salon's services array
        await db.salons.update_one(
            {"salon_id": service["salon_id"]},
            {"$pull": {"services": service_id}}
        )
        # Delete service
        result = await db.services.delete_one({"service_id": service_id})
        return result.deleted_count > 0
    return False

async def get_all_services() -> List[Service]:
    db = Database()
    services = await db.services.find().to_list(length=None)
    return [Service(**service) for service in services] 