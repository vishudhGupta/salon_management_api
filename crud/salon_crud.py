from typing import List, Optional, Dict, Any
from schemas.salon import (
    SalonCreate, Salon, generate_salon_id, SalonWorkingHours, 
    TimeSlot, ExpertWorkingHours, Appointment
)
from config.database import Database
import logging
from bson import ObjectId
from datetime import datetime, time, timedelta
from copy import deepcopy
from scripts.time_parse import deserialize_time_slots
from fastapi import HTTPException

logger = logging.getLogger(__name__)
def clean_object_ids(obj):
    """Recursively convert ObjectId to string in nested dicts/lists."""
    if isinstance(obj, dict):
        return {
            key: clean_object_ids(str(value) if isinstance(value, ObjectId) else value)
            for key, value in obj.items()
        }
    elif isinstance(obj, list):
        return [clean_object_ids(item) for item in obj]
    return obj

async def create_salon(salon: SalonCreate) -> Salon:
    db = Database()  # Use the Database class directly since connect_db is already called
    salon_id = generate_salon_id(salon.name)
    salon_dict = salon.dict()
    salon_dict["salon_id"] = salon_id
    salon_dict["services"] = []  # Initialize empty services array
    salon_dict["experts"] = []   # Initialize empty experts array
    salon_dict["appointments"] = []
    salon_dict["ratings"] = []
    salon_dict["average_rating"] = 0.0
    salon_dict["total_ratings"] = 0
    
    # Create the salon
    await db.salons.insert_one(salon_dict)
    
    return Salon(**salon_dict)

async def get_salon(salon_id: str) -> Optional[Salon]:
    """Get a specific salon by ID."""
    try:
        db = Database()
        logger.info(f"Fetching salon with ID: {salon_id}")
        
        salon = await db.salons.find_one({"salon_id": salon_id})
        if salon:
            logger.info(f"Found salon: {salon.get('name', 'Unknown')}")
            # Handle appointments by initializing them as empty list
            if "appointments" in salon:
                salon["appointments"] = []
            return Salon(**salon)
        
        logger.warning(f"No salon found with ID: {salon_id}")
        return None
    except Exception as e:
        logger.error(f"Error fetching salon {salon_id}: {str(e)}", exc_info=True)
        raise Exception(f"Error fetching salon: {str(e)}")

async def get_salons_by_service(service_id: str) -> List[Salon]:
    try:
        db = Database()
        # Find salons that have this service in their services array
        salons = await db.salons.find({
            "services": service_id
        }).to_list(length=None)
        # Handle appointments by initializing them as empty lists
        salon_list = []
        for salon in salons:
            if "appointments" in salon:
                salon["appointments"] = []
            salon_list.append(Salon(**salon))
        return salon_list
    except Exception as e:
        logger.error(f"Error fetching salons by service {service_id}: {str(e)}", exc_info=True)
        raise Exception(f"Error fetching salons by service: {str(e)}")

async def get_salons_by_expert(expert_id: str) -> List[Salon]:
    try:
        db = Database()
        # Find salons that have this expert in their experts array
        salons = await db.salons.find({
            "experts": expert_id
        }).to_list(length=None)
        # Handle appointments by initializing them as empty lists
        salon_list = []
        for salon in salons:
            if "appointments" in salon:
                salon["appointments"] = []
            salon_list.append(Salon(**salon))
        return salon_list
    except Exception as e:
        logger.error(f"Error fetching salons by expert {expert_id}: {str(e)}", exc_info=True)
        raise Exception(f"Error fetching salons by expert: {str(e)}")



async def update_salon(salon_id: str, salon_data: dict) -> Optional[Salon]:
    try:
        db = Database()
        update_result = await db.salons.update_one(
            {"salon_id": salon_id},
            {"$set": salon_data}
        )
        if update_result.modified_count:
            return await get_salon(salon_id)
        logger.warning(f"No salon was updated with ID: {salon_id}")
        return None
    except Exception as e:
        logger.error(f"Error updating salon {salon_id}: {str(e)}", exc_info=True)
        raise Exception(f"Error updating salon: {str(e)}")

async def get_all_salons() -> List[Salon]:
    """Get all salons from the database."""
    try:
        db = Database()  # This will raise an exception if DB is not initialized
        logger.info("Fetching all salons from database")
        
        # First check if the collection exists and has documents
        count = await db.salons.count_documents({})
        if count == 0:
            logger.warning("No salons found in database")
            return []
            
        # Fetch all salons
        salons = await db.salons.find().to_list(length=None)
        logger.info(f"Successfully fetched {len(salons)} salons")
        
        # Convert to Salon objects, handling appointments properly
        salon_list = []
        for salon in salons:
            # Ensure required fields have default values
            salon_data = {
                "salon_id": salon.get("salon_id", ""),
                "name": salon.get("name", ""),
                "address": salon.get("address", ""),
                "phone": salon.get("phone", ""),
                "description": salon.get("description", ""),
                "services": salon.get("services", []),
                "experts": salon.get("experts", []),
                "appointments": salon.get("appointments", []),
                "average_rating": float(salon.get("average_rating", 0.0)),
                "total_ratings": int(salon.get("total_ratings", 0)),
                "created_at": salon.get("created_at", datetime.utcnow()),
                "updated_at": salon.get("updated_at", datetime.utcnow())
            }
            
            # Add working hours if they exist
            if "working_hours" in salon:
                salon_data["working_hours"] = salon["working_hours"]
            
            # Add expert working hours if they exist
            if "expert_working_hours" in salon:
                salon_data["expert_working_hours"] = salon["expert_working_hours"]
            
            try:
                salon_list.append(Salon(**salon_data))
            except Exception as e:
                logger.error(f"Error converting salon data: {str(e)}")
                continue
        
        return salon_list
    except Exception as e:
        logger.error(f"Error fetching salons: {str(e)}", exc_info=True)
        # Re-raise the exception to be handled by the caller
        raise Exception(f"Error fetching salons: {str(e)}")

async def add_service_to_salon(salon_id: str, service_id: str) -> Optional[Salon]:
    try:
        db = Database()
        # First verify that the service exists
        service = await db.services.find_one({"service_id": service_id})
        if not service:
            logger.warning(f"No service found with ID: {service_id}")
            return None
            
        update_result = await db.salons.update_one(
            {"salon_id": salon_id},
            {"$addToSet": {"services": service_id}}
        )
        if update_result.modified_count:
            return await get_salon(salon_id)
        logger.warning(f"No salon was updated with ID: {salon_id}")
        return None
    except Exception as e:
        logger.error(f"Error adding service {service_id} to salon {salon_id}: {str(e)}", exc_info=True)
        raise Exception(f"Error adding service to salon: {str(e)}")

async def remove_service_from_salon(salon_id: str, service_id: str) -> Optional[Salon]:
    try:
        db = Database()
        update_result = await db.salons.update_one(
            {"salon_id": salon_id},
            {"$pull": {"services": service_id}}
        )
        if update_result.modified_count:
            return await get_salon(salon_id)
        logger.warning(f"No salon was updated with ID: {salon_id}")
        return None
    except Exception as e:
        logger.error(f"Error removing service {service_id} from salon {salon_id}: {str(e)}", exc_info=True)
        raise Exception(f"Error removing service from salon: {str(e)}")

async def add_expert_to_salon(salon_id: str, expert_id: str) -> Optional[Salon]:
    try:
        db = Database()
        # First verify that the expert exists
        expert = await db.experts.find_one({"expert_id": expert_id})
        if not expert:
            logger.warning(f"No expert found with ID: {expert_id}")
            return None
            
        update_result = await db.salons.update_one(
            {"salon_id": salon_id},
            {"$addToSet": {"experts": expert_id}}
        )
        if update_result.modified_count:
            return await get_salon(salon_id)
        logger.warning(f"No salon was updated with ID: {salon_id}")
        return None
    except Exception as e:
        logger.error(f"Error adding expert {expert_id} to salon {salon_id}: {str(e)}", exc_info=True)
        raise Exception(f"Error adding expert to salon: {str(e)}")

async def remove_expert_from_salon(salon_id: str, expert_id: str) -> Optional[Salon]:
    try:
        db = Database()
        update_result = await db.salons.update_one(
            {"salon_id": salon_id},
            {"$pull": {"experts": expert_id}}
        )
        if update_result.modified_count:
            return await get_salon(salon_id)
        logger.warning(f"No salon was updated with ID: {salon_id}")
        return None
    except Exception as e:
        logger.error(f"Error removing expert {expert_id} from salon {salon_id}: {str(e)}", exc_info=True)
        raise Exception(f"Error removing expert from salon: {str(e)}")

async def get_salon_services(salon_id: str) -> List[str]:
    """Get all services for a specific salon"""
    try:
        db = Database()
        logger.info(f"Fetching services for salon {salon_id}")
        salon = await db.salons.find_one({"salon_id": salon_id})
        if salon and "services" in salon:
            logger.info(f"Found {len(salon['services'])} services for salon {salon_id}")
            return salon["services"]
        logger.warning(f"No services found for salon {salon_id}")
        return []
    except Exception as e:
        logger.error(f"Error fetching services for salon {salon_id}: {str(e)}", exc_info=True)
        raise Exception(f"Error fetching salon services: {str(e)}")

async def get_salon_experts(salon_id: str) -> List[str]:
    """Get all experts for a specific salon"""
    try:
        db = Database()
        logger.info(f"Fetching experts for salon {salon_id}")
        salon = await db.salons.find_one({"salon_id": salon_id})
        if salon and "experts" in salon:
            logger.info(f"Found {len(salon['experts'])} experts for salon {salon_id}")
            return salon["experts"]
        logger.warning(f"No experts found for salon {salon_id}")
        return []
    except Exception as e:
        logger.error(f"Error fetching experts for salon {salon_id}: {str(e)}", exc_info=True)
        raise Exception(f"Error fetching salon experts: {str(e)}") 
    
async def get_salon_dashboard(salon_id: str) -> Optional[dict]:
    db = Database()

    salon = await db.salons.find_one({"salon_id": salon_id})
    if not salon:
        return None

    salon = clean_object_ids(salon)

    # Fetch services
    service_ids = salon.get("services", [])
    services_raw = await db.services.find({"service_id": {"$in": service_ids}}).to_list(None)
    services = [clean_object_ids(s) for s in services_raw]

    # Fetch experts
    expert_ids = salon.get("experts", [])
    experts_raw = await db.experts.find({"expert_id": {"$in": expert_ids}}).to_list(None)
    experts = [clean_object_ids(e) for e in experts_raw]

    # Fetch appointments related to the salon
    appointments_raw = await db.appointments.find({"salon_id": salon_id}).to_list(None)

    appointments = []
    for appt in appointments_raw:
        appt = clean_object_ids(appt)

        user = await db.users.find_one({"user_id": appt["user_id"]})
        expert = await db.experts.find_one({"expert_id": appt["expert_id"]})
        service = await db.services.find_one({"service_id": appt["service_id"]})

        appt["user"] = clean_object_ids(user)
        appt["expert"] = clean_object_ids(expert)
        appt["service"] = clean_object_ids(service)

        appointments.append(appt)

    # Fix rating and review defaults
    salon["ratings"] = float(salon.get("ratings", 0.0)) if isinstance(salon.get("ratings"), (int, float)) else 0.0
    salon["total_reviews"] = int(salon.get("total_reviews", 0))

    salon["services"] = services
    salon["experts"] = experts
    salon["appointments"] = appointments
    salon["ratings"] = float(salon.get("ratings", 0.0)) if isinstance(salon.get("ratings"), (int, float)) else 0.0
    
    return clean_object_ids(salon)


async def create_salon_working_hours(salon_id: str, working_hours: SalonWorkingHours) -> SalonWorkingHours:
    """Create working hours for a salon"""
    salon = await get_salon(salon_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    
    salon_working_hours = SalonWorkingHours(
        salon_id=salon_id,
        is_available=[True] * 7,  # Default to all days available
        updated_at=datetime.utcnow()
    )
    
    # Update in the salons collection
    db = Database()
    await db.salons.update_one(
        {"salon_id": salon_id},
        {"$set": {"working_hours": salon_working_hours.dict()}},
        upsert=True
    )
    return salon_working_hours

async def update_salon_working_hours(salon_id: str, working_hours: SalonWorkingHours) -> SalonWorkingHours:
    """Update working hours for a salon"""
    db = Database()
    working_hours_dict = working_hours.dict()
    working_hours_dict["updated_at"] = datetime.utcnow()
    
    await db.salons.update_one(
        {"salon_id": salon_id},
        {"$set": {"working_hours": working_hours_dict}},
        upsert=True
    )
    return working_hours

async def get_salon_working_hours(salon_id: str) -> Optional[SalonWorkingHours]:
    """Get working hours for a salon"""
    db = Database()
    working_hours = await db.salons.find_one({"salon_id": salon_id})
    if working_hours and "working_hours" in working_hours:
        return SalonWorkingHours(**working_hours["working_hours"])
    return None



async def get_available_time_slots(salon_id: str, date: datetime) -> List[TimeSlot]:
    """Get available time slots for a salon on a specific date"""
    db = Database()
    
    # Get salon's working hours
    working_hours = await get_salon_working_hours(salon_id)
    if not working_hours:
        return []
    
    # Get day of week (0 = Monday, 6 = Sunday)
    day_of_week = date.weekday()
    
    # Check if salon is available on this day
    if not working_hours.is_available[day_of_week]:
        return []
    
    # If salon is available, return all time slots from 9 AM to 9 PM
    slots = []
    start_time = time(9, 0)  # 9 AM
    end_time = time(21, 0)   # 9 PM
    
    current_time = start_time
    while current_time < end_time:
        slots.append(TimeSlot(
            start_time=current_time,
            end_time=time(current_time.hour + 1, current_time.minute)
        ))
        current_time = time(current_time.hour + 1, current_time.minute)
    
    return slots


async def update_expert_working_hours(salon_id: str, expert_id: str, working_hours: ExpertWorkingHours) -> Optional[ExpertWorkingHours]:
    """Update working hours for an expert in a salon"""
    db = Database()
    
    # Deep copy to avoid mutation
    working_hours_dict = deepcopy(working_hours.dict())
    working_hours_dict["updated_at"] = datetime.utcnow()

    # Update in MongoDB
    result = await db.salons.update_one(
        {"salon_id": salon_id},
        {"$set": {f"expert_working_hours.{expert_id}": working_hours_dict}}
    )

    if result.modified_count:
        return working_hours
    return None


async def get_expert_working_hours(salon_id: str, expert_id: str) -> Optional[ExpertWorkingHours]:
    """Get working hours for an expert in a salon"""
    db = Database()
    salon = await db.salons.find_one({"salon_id": salon_id})
    if salon and "expert_working_hours" in salon and expert_id in salon["expert_working_hours"]:
        wh = salon["expert_working_hours"][expert_id]
        return ExpertWorkingHours(**wh)
    return None


async def get_all_expert_working_hours(salon_id: str) -> Dict[str, ExpertWorkingHours]:
    """Get working hours for all experts in a salon"""
    db = Database()
    salon = await db.salons.find_one({"salon_id": salon_id})
    if salon and "expert_working_hours" in salon:
        return {
            expert_id: ExpertWorkingHours(**wh)
            for expert_id, wh in salon["expert_working_hours"].items()
        }
    return {}


async def remove_expert_working_hours(salon_id: str, expert_id: str) -> bool:
    """Remove working hours for an expert from a salon"""
    db = Database()
    result = await db.salons.update_one(
        {"salon_id": salon_id},
        {"$unset": {f"expert_working_hours.{expert_id}": ""}}
    )
    return result.modified_count > 0