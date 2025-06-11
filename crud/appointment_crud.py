from typing import List, Optional
from schemas.appointment import AppointmentCreate, Appointment, generate_appointment_id, UserDetails, ExpertDetails, ServiceDetails
from config.database import Database
from datetime import datetime
from fastapi import HTTPException
from services.notification_service import NotificationService
from services.twilio_service import TwilioService
from crud.rating_crud import add_rating
import logging
import re
import uuid

# Set up logging
logger = logging.getLogger(__name__)

async def check_expert_availability(expert_id: str, appointment_date: datetime, appointment_time: str) -> bool:
    db = Database()

    # Convert appointment_time to datetime.time
    hour, minute = map(int, appointment_time.split(":"))
    slot_time = f"{hour:02d}:{minute:02d}"

    # Get weekday (e.g., 'monday')
    weekday = appointment_date.strftime('%A').lower()

    # Check expert's availability for this weekday and time
    expert = await db.experts.find_one({"expert_id": expert_id})
    if not expert:
        return False

    availability = expert.get("availability", {})
    slots = availability.get(weekday, {}).get("slots", [])

    matching_slot = next((slot for slot in slots if slot["start_time"] == slot_time and slot["is_available"]), None)
    if not matching_slot:
        return False

    # Also check if already booked at this exact time
    existing_appointment = await db.appointments.find_one({
        "expert.expert_id": expert_id,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "status": {"$in": ["confirmed", "pending"]}
    })

    return existing_appointment is None


async def create_appointment(appointment: AppointmentCreate) -> Appointment:
    """Create a new appointment in the database"""
    try:
        db = Database()

        # Validate user and get user details
        user = await db.users.find_one({"user_id": appointment.user.user_id})
        if not user:
            raise ValueError(f"User with ID {appointment.user.user_id} not found")
        
        user_details = UserDetails(
            user_id=user["user_id"],
            name=user["name"],
            email=user["email"],
            phone_number=user["phone_number"],
            address=user["address"]
        )

        # Validate salon
        salon = await db.salons.find_one({"salon_id": appointment.salon_id})
        if not salon:
            raise ValueError(f"Salon with ID {appointment.salon_id} not found")

        # Validate service and get service details
        service = await db.services.find_one({"service_id": appointment.service.service_id})
        if not service:
            raise ValueError(f"Service with ID {appointment.service.service_id} not found")
        
        service_details = ServiceDetails(
            service_id=service["service_id"],
            name=service["name"],
            description=service.get("description"),
            cost=service["cost"],
            duration=service["duration"]
        )

        # Validate expert & check availability if expert is provided
        expert_details = None
        if appointment.expert:
            expert = await db.experts.find_one({
                "expert_id": appointment.expert.expert_id,
                "salon_id": appointment.salon_id
            })
            if not expert:
                raise ValueError(f"Expert with ID {appointment.expert.expert_id} not found in salon {appointment.salon_id}")

            expert_details = ExpertDetails(
                expert_id=expert["expert_id"],
                name=expert["name"],
                phone=expert["phone"],
                address=expert["address"],
                specialization=expert.get("specialization"),
                experties=expert.get("experties")
            )

            # Get day name (e.g., "monday")
            weekday = str(appointment.appointment_date.weekday())  # Convert to string index (0-6)
            
            # Parse the appointment time
            try:
                appointment_time = datetime.strptime(appointment.appointment_time, "%I:%M %p").time()
                hour = appointment_time.hour
                availability_index = hour - 9  # 9am is index 0
            except ValueError:
                raise ValueError(f"Invalid time format: {appointment.appointment_time}")

            # Get expert's availability from expert_availability collection
            availability_doc = await db.expert_availability.find_one({"expert_id": appointment.expert.expert_id})
            if not availability_doc:
                # If no availability document exists, create one with default availability
                availability_doc = {
                    "expert_id": appointment.expert.expert_id,
                    "salon_id": appointment.salon_id,
                    "is_available": True,
                    "availability": {str(i): [True] * 13 for i in range(7)}
                }
                await db.expert_availability.insert_one(availability_doc)

            # Check if expert is available at this time
            availability = availability_doc.get("availability", {})
            day_slots = availability.get(weekday, [True] * 13)

            if availability_index < 0 or availability_index >= len(day_slots) or not day_slots[availability_index]:
                raise ValueError(f"Expert not available at {appointment.appointment_time} on {appointment.appointment_date.strftime('%Y-%m-%d')}")

            # Check for time conflict with other appointments
            conflict = await db.appointments.find_one({
                "expert.expert_id": appointment.expert.expert_id,
                "appointment_date": appointment.appointment_date,
                "appointment_time": appointment.appointment_time,
                "status": {"$in": ["pending", "confirmed"]}
            })
            if conflict:
                raise ValueError(f"Expert already has a booking at {appointment.appointment_time} on {appointment.appointment_date.strftime('%Y-%m-%d')}")

        # Generate appointment ID
        appointment_id = generate_appointment_id(
            salon_id=appointment.salon_id,
            user_id=appointment.user.user_id
        )

        # Create appointment document with detailed information
        appointment_dict = {
            "appointment_id": appointment_id,
            "salon_id": appointment.salon_id,
            "user": user_details.dict(),
            "service": service_details.dict(),
            "expert": expert_details.dict() if expert_details else None,
            "appointment_date": appointment.appointment_date,
            "appointment_time": appointment.appointment_time,
            "notes": appointment.notes,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "expert_confirmed": False
        }

        # Insert appointment
        await db.appointments.insert_one(appointment_dict)

        # Update references
        try:
            await db.users.update_one(
                {"user_id": appointment.user.user_id},
                {"$addToSet": {"appointments": appointment_id}}
            )
            await db.salons.update_one(
                {"salon_id": appointment.salon_id},
                {"$addToSet": {"appointments": appointment_id}}
            )
            if expert_details:
                await db.experts.update_one(
                    {"expert_id": expert_details.expert_id},
                    {"$addToSet": {"appointments": appointment_id}}
                )
        except Exception as e:
            logging.error(f"Error updating references for appointment {appointment_id}: {str(e)}")
            await db.appointments.delete_one({"appointment_id": appointment_id})
            raise

        return Appointment(**appointment_dict)

    except Exception as e:
        logging.error(f"Error creating appointment: {str(e)}", exc_info=True)
        raise


async def get_appointment(appointment_id: str) -> Optional[Appointment]:
    db = Database()
    appointment = await db.appointments.find_one({"appointment_id": appointment_id})
    return Appointment(**appointment) if appointment else None

async def get_user_appointments(user_id: str) -> List[Appointment]:
    db = Database()
    appointments = await db.appointments.find({"user.user_id": user_id}).to_list(length=None)
    return [Appointment(**appointment) for appointment in appointments]

async def get_salon_appointments(salon_id: str) -> List[Appointment]:
    db = Database()
    appointments = await db.appointments.find({"salon_id": salon_id}).to_list(length=None)
    return [Appointment(**appointment) for appointment in appointments]

async def get_expert_appointments(expert_id: str) -> List[Appointment]:
    db = Database()
    appointments = await db.appointments.find({"expert.expert_id": expert_id}).to_list(length=None)
    return [Appointment(**appointment) for appointment in appointments]

async def update_appointment(appointment_id: str, appointment_data: dict) -> Optional[Appointment]:
    db = Database()
    update_result = await db.appointments.update_one(
        {"appointment_id": appointment_id},
        {"$set": appointment_data}
    )
    if update_result.modified_count:
        return await get_appointment(appointment_id)
    return None

async def cancel_appointment(appointment_id: str) -> Optional[Appointment]:
    db = Database()
    update_result = await db.appointments.update_one(
        {"appointment_id": appointment_id},
        {"$set": {"status": "cancelled"}}
    )
    if update_result.modified_count:
        return await get_appointment(appointment_id)
    return None

async def confirm_appointment(appointment_id: str) -> Optional[Appointment]:
    db = Database()
    update_result = await db.appointments.update_one(
        {"appointment_id": appointment_id},
        {"$set": {"status": "confirmed"}}
    )
    if update_result.modified_count:
        return await get_appointment(appointment_id)
    return None

async def get_upcoming_appointments(user_id: str) -> List[Appointment]:
    db = Database()
    current_time = datetime.utcnow()
    appointments = await db.appointments.find({
        "user.user_id": user_id,
        "appointment_date": {"$gt": current_time},
        "status": "confirmed"
    }).to_list(length=None)
    return [Appointment(**appointment) for appointment in appointments]

async def get_all_appointments() -> List[Appointment]:
    db = Database()
    appointments = await db.appointments.find().to_list(length=None)
    return [Appointment(**appointment) for appointment in appointments]

async def confirm_expert_appointment(appointment_id: str, expert_id: str) -> Optional[Appointment]:
    """Allow expert to confirm their appointment"""
    db = Database()
    appointment = await get_appointment(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if not appointment.expert or appointment.expert.expert_id != expert_id:
        raise HTTPException(status_code=403, detail="Not authorized to confirm this appointment")
    
    update_result = await db.appointments.update_one(
        {"appointment_id": appointment_id},
        {"$set": {"expert_confirmed": True}}
    )
    
    if update_result.modified_count:
        # Send notification to user
        notification_service = NotificationService(db)
        await notification_service.send_appointment_status_notification(
            user_id=appointment.user.user_id,
            appointment_id=appointment_id,
            status="expert_confirmed"
        )
        return await get_appointment(appointment_id)
    return None

async def complete_appointment(appointment_id: str, booking_service = None) -> Optional[Appointment]:
    """Complete an appointment and send review request"""
    try:
        print(f"\n[DEBUG] Starting complete_appointment for appointment_id: {appointment_id}")
        db = Database()
        
        # Get the appointment
        appointment = await db.appointments.find_one({"appointment_id": appointment_id})
        if not appointment:
            print("[DEBUG] Appointment not found")
            return None
            
        print(f"[DEBUG] Found appointment: {appointment}")
            
        # Update appointment status
        update_result = await db.appointments.update_one(
            {"appointment_id": appointment_id},
            {
                "$set": {
                    "status": "completed",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        print(f"[DEBUG] Appointment status update result: {update_result.modified_count}")
        
        if update_result.modified_count:
            # Send review request notification
            if booking_service:
                await booking_service.send_review_request(appointment_id)
            return await get_appointment(appointment_id)
        return None
        
    except Exception as e:
        logging.error(f"Error completing appointment: {str(e)}", exc_info=True)
        raise

async def handle_review_response(appointment_id: str, review_message: str):
    """Handle user's review response"""
    try:
        db = Database()
        logger.debug(f"Starting handle_review_response for appointment_id: {appointment_id}")
        logger.debug(f"Review message: {review_message}")
        
        # Get appointment details
        appointment = await db.appointments.find_one({"appointment_id": appointment_id})
        if not appointment:
            raise ValueError("Appointment not found")
            
        logger.debug(f"Found appointment: {appointment}")
            
        # Get user details from the nested user object
        user = await db.users.find_one({"user_id": appointment["user"]["user_id"]})
        if not user:
            raise ValueError("User not found")

        # Parse the review message to extract rating and comment
        try:
            # First try to parse as just a number
            rating = int(review_message.strip())
            comment = ""
        except ValueError:
            # If not a number, try to parse as "rating - comment" format
            parts = review_message.replace(" - ", "-").split('-', 1)
            if len(parts) >= 1:
                try:
                    rating = int(parts[0].strip())
                    comment = parts[1].strip() if len(parts) == 2 else ""
                except ValueError:
                    raise ValueError("Please provide a rating between 1-5, followed by your comments (optional).")
            else:
                raise ValueError("Please provide a rating between 1-5, followed by your comments (optional).")

        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")

        # Update the salon rating using the existing add_rating function
        await add_rating(
            salon_id=appointment["salon_id"],
            user_id=user["user_id"],
            rating=rating,
            comment=comment
        )

        # Send thank you message
        twilio_service = TwilioService()
        await twilio_service.send_sms(
            user["phone_number"],
            "Thank you for your feedback! We appreciate your input. 😊\n\nSend 'hi' to book another service."
        )
        
        return {"status": "success", "message": "Review saved successfully"}
        
    except Exception as e:
        logger.error(f"Error in handle_review_response: {str(e)}", exc_info=True)
        raise 