from typing import List, Optional, Dict, Any
from schemas.salon import (
    SalonCreate, Salon, SalonUpdate, generate_salon_id,
    TimeSlot, Appointment, ExpertAvailability
)
from config.database import Database
import logging
from bson import ObjectId
from datetime import datetime, time, timedelta, timezone
from copy import deepcopy
from scripts.time_parse import deserialize_time_slots
from fastapi import HTTPException
from crud.expert_crud import get_expert, get_experts_by_salon
from crud.appointment_crud import get_salon_appointments
from collections import Counter
import re
import random

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

async def get_salon_services(salon_id: str) -> Optional[List[str]]:
    """Get all services for a salon"""
    try:
        salon = await get_salon(salon_id)
        if not salon:
            return None
        return salon.services
    except Exception as e:
        logger.error(f"Error getting salon services: {str(e)}", exc_info=True)
        raise Exception(f"Error getting salon services: {str(e)}")



async def get_salon_experts(salon_id: str) -> Optional[List[str]]:
    """Get all experts for a salon"""
    try:
        salon = await get_salon(salon_id)
        if not salon:
            return None
        return salon.experts
    except Exception as e:
        logger.error(f"Error getting salon experts: {str(e)}", exc_info=True)
        raise Exception(f"Error getting salon experts: {str(e)}")


async def get_salon_dashboard(salon_id: str) -> Optional[dict]:
    """Get salon dashboard data"""
    try:
        db = Database()
        salon = await db.salons.find_one({"salon_id": salon_id})
        if not salon:
            return None
        
        # Get total appointments
        total_appointments = await db.appointments.count_documents({"salon_id": salon_id})
        
        # Get total revenue
        revenue = await db.appointments.aggregate([
            {"$match": {"salon_id": salon_id}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]).to_list(1)
        total_revenue = revenue[0]["total"] if revenue else 0
        
        # Get experts with their availability
        experts = []
        for expert_id in salon.get("experts", []):
            expert = await get_expert(expert_id)
            if expert:
                availability = await get_expert_availability(salon_id, expert_id)
                experts.append({
                    "expert_id": expert.expert_id,
                    "name": expert.name,
                    "phone": expert.phone if hasattr(expert, 'phone') else None,
                    "is_available": availability.is_available if availability else True,
                    "availability": availability.availability if availability else {
                        str(i): [True] * 13 for i in range(7)
                    }
                })
        
        # Get services
        services = []
        for service_id in salon.get("services", []):
            service = await db.services.find_one({"service_id": service_id})
            if service:
                services.append({
                    "service_id": service["service_id"],
                    "name": service["name"],
                    "cost": service["cost"],
                    "duration": service["duration"]
                })
        
        # Get appointments
        appointments = []
        salon_appointments = await db.appointments.find({"salon_id": salon_id}).to_list(length=None)
        for apt in salon_appointments:
            user = await db.users.find_one({"user_id": apt["user_id"]})
            service = await db.services.find_one({"service_id": apt["service_id"]})
            expert = await db.experts.find_one({"expert_id": apt["expert_id"]})
            
            if user and service and expert:
                # Convert appointment time from 12-hour to 24-hour format
                try:
                    time_obj = datetime.strptime(apt["appointment_time"], "%I:%M %p")
                    formatted_time = time_obj.strftime("%H:%M")
                except ValueError:
                    # If time is already in 24-hour format, use it as is
                    formatted_time = apt["appointment_time"]
                
                appointments.append({
                    "appointment_id": apt["appointment_id"],
                    "appointment_date": apt["appointment_date"],
                    "appointment_time": formatted_time,
                    "status": apt["status"],
                    "user": {
                        "user_id": user["user_id"],
                        "name": user["name"],
                        "phone_number": user["phone_number"]
                    },
                    "service": {
                        "service_id": service["service_id"],
                        "name": service["name"],
                        "cost": service["cost"],
                        "duration": service["duration"]
                    },
                    "expert": {
                        "expert_id": expert["expert_id"],
                        "name": expert["name"],
                        "phone": expert.get("phone")
                    }
                })
        
        return {
            "salon_id": salon_id,
            "name": salon["name"],
            "address": salon["address"],
            "services": services,
            "experts": experts,
            "appointments": appointments,
            "ratings": salon.get("average_rating", 0.0),
            "total_reviews": salon.get("total_ratings", 0)
        }
    except Exception as e:
        logger.error(f"Error getting salon dashboard: {str(e)}", exc_info=True)
        raise Exception(f"Error getting salon dashboard: {str(e)}")

async def get_available_time_slots(salon_id: str, date: datetime, db: Database) -> List[TimeSlot]:
    """Get available time slots for a salon on a specific date"""
    try:
        # Initialize time slots from 9am to 9pm
        time_slots = []
        for hour in range(9, 21):  # 9 to 20 gives slots till 9PM
            time_slots.append(TimeSlot(
                start_time=time(hour, 0),
                end_time=time(hour + 1, 0),
                is_available=True
            ))

        # Get salon
        salon = await get_salon(salon_id)
        if not salon:
            return []

        # Get experts
        experts = await get_experts_by_salon(salon_id)
        if not experts:
            return []

        # Check slot availability
        for slot in time_slots:
            slot_available = False
            for expert in experts:
                hour_index = slot.start_time.hour - 9
                if hour_index < len(expert.availability) and expert.availability[hour_index]:
                    appointment = await db.appointments.find_one({
                        "salon_id": salon_id,
                        "expert_id": expert.expert_id,
                        "appointment_date": date,
                        "appointment_time": slot.start_time.strftime("%I:%M %p")
                    })
                    if not appointment:
                        slot_available = True
                        break
            slot.is_available = slot_available

        return [slot for slot in time_slots if slot.is_available]

    except Exception as e:
        logger.error(f"Error getting available time slots: {str(e)}", exc_info=True)
        raise Exception(f"Error getting available time slots: {str(e)}")



async def get_expert_availability(salon_id: str, expert_id: str) -> Optional[ExpertAvailability]:
    """Get an expert's availability"""
    try:
        db = Database()
        # Get availability directly from expert_availability collection
        availability_doc = await db.expert_availability.find_one({
            "expert_id": expert_id,
            "salon_id": salon_id
        })
        
        if not availability_doc:
            # If no availability document exists, create one with default availability
            availability_doc = {
                "expert_id": expert_id,
                "salon_id": salon_id,
                "is_available": True,
                "availability": {
                    "0": [True] * 13,  # Sunday
                    "1": [True] * 13,  # Monday
                    "2": [True] * 13,  # Tuesday
                    "3": [True] * 13,  # Wednesday
                    "4": [True] * 13,  # Thursday
                    "5": [True] * 13,  # Friday
                    "6": [True] * 13   # Saturday
                }
            }
            await db.expert_availability.insert_one(availability_doc)
        
        return ExpertAvailability(**availability_doc)
    except Exception as e:
        logger.error(f"Error getting expert availability: {str(e)}", exc_info=True)
        raise Exception(f"Error getting expert availability: {str(e)}")

async def update_expert_availability(salon_id: str, expert_id: str, weekday: str, availability: List[bool]) -> bool:
    """Update an expert's availability for a specific weekday"""
    try:
        if len(availability) != 13:
            return False
            
        if weekday not in ["0", "1", "2", "3", "4", "5", "6"]:
            return False
        
        db = Database()
        
        # Get current availability document
        availability_doc = await db.expert_availability.find_one({
            "expert_id": expert_id,
            "salon_id": salon_id
        })
        
        if not availability_doc:
            # Create new availability document if it doesn't exist
            availability_doc = {
                "expert_id": expert_id,
                "salon_id": salon_id,
                "is_available": True,
                "availability": {
                    "0": [True] * 13,  # Sunday
                    "1": [True] * 13,  # Monday
                    "2": [True] * 13,  # Tuesday
                    "3": [True] * 13,  # Wednesday
                    "4": [True] * 13,  # Thursday
                    "5": [True] * 13,  # Friday
                    "6": [True] * 13   # Saturday
                }
            }
        
        # Update availability for the specific weekday
        availability_doc["availability"][weekday] = availability
        
        # Update is_available based on if any day has any available slots
        availability_doc["is_available"] = any(
            any(slots) for slots in availability_doc["availability"].values()
        )
        
        # Update in expert_availability collection
        result = await db.expert_availability.update_one(
            {"expert_id": expert_id, "salon_id": salon_id},
            {"$set": availability_doc},
            upsert=True
        )
        
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        logger.error(f"Error updating expert availability: {str(e)}", exc_info=True)
        raise Exception(f"Error updating expert availability: {str(e)}")

async def get_salon_statistics(salon_id: str, start_date: datetime, end_date: datetime) -> dict:
    """
    Get salon statistics including revenue, services used, and experts used within a date range.
    If only start_date is provided, statistics will be for that single day.
    """
    try:
        # Validate salon exists
        salon = await get_salon(salon_id)
        if not salon:
            raise ValueError("Salon not found")

        # Convert input dates to naive UTC for MongoDB
        if start_date.tzinfo is not None:
            start_date = start_date.astimezone(timezone.utc).replace(tzinfo=None)
        if end_date and end_date.tzinfo is not None:
            end_date = end_date.astimezone(timezone.utc).replace(tzinfo=None)

        # Set end_date to start_date if not provided
        if not end_date:
            end_date = start_date + timedelta(days=1)
        else:
            end_date = end_date + timedelta(days=1)  # Include the end date

        # Database-side filtering for appointments
        db = Database()
        appointments = await db.appointments.find({
            "salon_id": salon_id,
            "appointment_date": {
                "$gte": start_date,
                "$lt": end_date
            }
        }).to_list(None)

        # Separate canceled appointments
        canceled_appointments = [apt for apt in appointments if apt["status"] == "cancelled"]
        appointments = [apt for apt in appointments if apt["status"] != "cancelled"]

        # Calculate total revenue from completed appointments
        total_revenue = sum(
            apt["service"]["cost"]
            for apt in appointments
            if apt["status"] == "completed"
        )

        # Get services used with counter
        service_counter = Counter()
        for apt in appointments:
            if apt["status"] == "completed":
                service_counter[apt["service"]["service_id"]] += 1

        # Batch fetch all services
        service_ids = list(service_counter.keys())
        services = await db.services.find({"service_id": {"$in": service_ids}}).to_list(None)
        services_dict = {s["service_id"]: s for s in services}

        # Create services_used list
        services_used = []
        for service_id, count in service_counter.most_common():
            service = services_dict.get(service_id)
            if service:
                services_used.append({
                    "service_id": service_id,
                    "name": service.get("name"),
                    "usage_count": count,
                    "revenue": service.get("cost", 0) * count
                })

        # Get experts used with counter
        expert_counter = Counter()
        for apt in appointments:
            if apt["status"] == "completed" and apt.get("expert"):
                expert_counter[apt["expert"]["expert_id"]] += 1

        # Batch fetch all experts
        expert_ids = list(expert_counter.keys())
        experts = await db.experts.find({"expert_id": {"$in": expert_ids}}).to_list(None)
        experts_dict = {e["expert_id"]: e for e in experts}

        # Create experts_used list
        experts_used = []
        for expert_id, count in expert_counter.most_common():
            expert = experts_dict.get(expert_id)
            if expert:
                experts_used.append({
                    "expert_id": expert_id,
                    "name": expert.get("name"),
                    "usage_count": count
                })

        # Transform appointments to match the schema
        def transform_appointment(apt):
            return {
                "appointment_id": apt["appointment_id"],
                "user_id": apt["user"]["user_id"],
                "salon_id": apt["salon_id"],
                "service_id": apt["service"]["service_id"],
                "expert_id": apt["expert"]["expert_id"] if apt.get("expert") else None,
                "appointment_date": apt["appointment_date"],
                "appointment_time": apt["appointment_time"],
                "status": apt["status"],
                "created_at": apt["created_at"]
            }

        appointments_dict = [transform_appointment(apt) for apt in appointments]
        canceled_appointments_dict = [transform_appointment(apt) for apt in canceled_appointments]

        return {
            "total_revenue": total_revenue,
            "services_used": services_used,
            "experts_used": experts_used,
            "appointments": appointments_dict,
            "canceled_appointments": canceled_appointments_dict
        }

    except Exception as e:
        logger.error(f"Error getting salon statistics: {str(e)}", exc_info=True)
        raise