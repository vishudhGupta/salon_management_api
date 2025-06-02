from typing import List, Optional
from schemas.service import Service, ServiceCreate
from config.database import Database
import re
import random
import string
from datetime import datetime
from bson import ObjectId

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
    """Create a new service"""
    db = Database()
    service_dict = service.dict()
    service_dict["created_at"] = datetime.now()
    service_dict["updated_at"] = datetime.now()
    service_dict["service_id"] = generate_service_id(service.name)
    
    result = await db.services.insert_one(service_dict)
    service_dict["_id"] = result.inserted_id
    
    # Update salon's services array
    await db.salons.update_one(
        {"salon_id": service.salon_id},
        {"$addToSet": {"services": service_dict["service_id"]}}
    )
    
    return Service(**service_dict)

async def get_service(service_id: str) -> Optional[Service]:
    """Get a service by ID"""
    db = Database()
    service = await db.services.find_one({"service_id": service_id})
    if service:
        return Service(**service)
    return None

async def get_salon_services(salon_id: str) -> List[Service]:
    db = Database()
    services = await db.services.find({"salon_id": salon_id}).to_list(length=None)
    return [Service(**service) for service in services]

async def update_service(service_id: str, service_data: dict) -> Optional[Service]:
    """Update a service with the provided data"""
    db = Database()
    # Add updated_at timestamp
    service_data["updated_at"] = datetime.now()
    
    # Update the service
    result = await db.services.update_one(
        {"service_id": service_id},
        {"$set": service_data}
    )
    
    if result.modified_count:
        # Get the updated service
        updated_service = await get_service(service_id)
        return updated_service
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
    """Get all services"""
    db = Database()
    services = await db.services.find().to_list(length=None)
    return [Service(**service) for service in services]

async def get_services_by_category(category: str) -> List[Service]:
    """Get services by category"""
    db = Database()
    services = await db.services.find({"category": category}).to_list(length=None)
    return [Service(**service) for service in services] 