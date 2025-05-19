from typing import List, Optional
from schemas.salon import SalonCreate, Salon, generate_salon_id
from config.database import Database
import logging

logger = logging.getLogger(__name__)

async def create_salon(salon: SalonCreate) -> Salon:
    db = Database()  # Use the Database class directly since connect_db is already called
    salon_id = generate_salon_id(salon.shop_owner_id)
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
    
    # Update shop owner's salons array
    await db.shop_owners.update_one(
        {"shop_owner_id": salon.shop_owner_id},
        {"$addToSet": {"salons": salon_id}}
    )
    
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

async def get_salons_by_owner(shop_owner_id: str) -> List[Salon]:
    try:
        db = Database()
        salons = await db.salons.find({"shop_owner_id": shop_owner_id}).to_list(length=None)
        # Handle appointments by initializing them as empty lists
        salon_list = []
        for salon in salons:
            if "appointments" in salon:
                salon["appointments"] = []
            salon_list.append(Salon(**salon))
        return salon_list
    except Exception as e:
        logger.error(f"Error fetching salons by owner {shop_owner_id}: {str(e)}", exc_info=True)
        raise Exception(f"Error fetching salons by owner: {str(e)}")

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
            # Convert appointment IDs to Appointment objects
            if "appointments" in salon:
                # For now, we'll just initialize empty appointments array
                # In a real implementation, you would fetch the actual appointment data
                salon["appointments"] = []
            salon_list.append(Salon(**salon))
        
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