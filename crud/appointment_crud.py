from typing import List, Optional
from schemas.appointment import AppointmentCreate, Appointment, generate_appointment_id
from config.database import Database
from datetime import datetime
from fastapi import HTTPException
from services.notification_service import NotificationService
from services.twilio_service import TwilioService
from crud.rating_crud import add_rating
import logging
import re

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
        "expert_id": expert_id,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "status": {"$in": ["confirmed", "pending"]}
    })

    return existing_appointment is None


async def create_appointment(appointment: AppointmentCreate) -> Appointment:
    """Create a new appointment in the database"""
    try:
        db = Database()

        # Validate user
        user = await db.users.find_one({"user_id": appointment.user_id})
        if not user:
            raise ValueError(f"User with ID {appointment.user_id} not found")

        # Validate salon
        salon = await db.salons.find_one({"salon_id": appointment.salon_id})
        if not salon:
            raise ValueError(f"Salon with ID {appointment.salon_id} not found")

        # Validate service
        service = await db.services.find_one({"service_id": appointment.service_id})
        if not service:
            raise ValueError(f"Service with ID {appointment.service_id} not found")

        # Validate expert & check availability
        if appointment.expert_id:
            expert = await db.experts.find_one({
                "expert_id": appointment.expert_id,
                "salon_id": appointment.salon_id
            })
            if not expert:
                raise ValueError(f"Expert with ID {appointment.expert_id} not found in salon {appointment.salon_id}")

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
            availability_doc = await db.expert_availability.find_one({"expert_id": appointment.expert_id})
            if not availability_doc:
                # If no availability document exists, create one with default availability
                availability_doc = {
                    "expert_id": appointment.expert_id,
                    "salon_id": appointment.salon_id,
                    "is_available": True,
                    "availability": {str(i): [True] * 13 for i in range(7)}
                }
                await db.expert_availability.insert_one(availability_doc)

            # Check if expert is available at this time
            availability = availability_doc.get("availability", {})
            day_slots = availability.get(weekday, [True] * 13)  # Default to all available

            if availability_index < 0 or availability_index >= len(day_slots) or not day_slots[availability_index]:
                raise ValueError(f"Expert not available at {appointment.appointment_time} on {appointment.appointment_date.strftime('%Y-%m-%d')}")

            # Check for time conflict with other appointments
            conflict = await db.appointments.find_one({
                "expert_id": appointment.expert_id,
                "appointment_date": appointment.appointment_date,
                "appointment_time": appointment.appointment_time,
                "status": {"$in": ["pending", "confirmed"]}
            })
            if conflict:
                raise ValueError(f"Expert already has a booking at {appointment.appointment_time} on {appointment.appointment_date.strftime('%Y-%m-%d')}")

        # Generate appointment ID
        appointment_id = generate_appointment_id(
            salon_id=appointment.salon_id,
            user_id=appointment.user_id
        )

        # Create appointment document
        appointment_dict = appointment.dict()
        appointment_dict["appointment_id"] = appointment_id
        appointment_dict["status"] = "pending"
        appointment_dict["created_at"] = datetime.utcnow()
        appointment_dict["expert_confirmed"] = False

        # Insert appointment
        await db.appointments.insert_one(appointment_dict)

        # Update references
        try:
            await db.users.update_one(
                {"user_id": appointment.user_id},
                {"$addToSet": {"appointments": appointment_id}}
            )
            await db.salons.update_one(
                {"salon_id": appointment.salon_id},
                {"$addToSet": {"appointments": appointment_id}}
            )
            if appointment.expert_id:
                await db.experts.update_one(
                    {"expert_id": appointment.expert_id},
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
    appointments = await db.appointments.find({"user_id": user_id}).to_list(length=None)
    return [Appointment(**appointment) for appointment in appointments]

async def get_salon_appointments(salon_id: str) -> List[Appointment]:
    db = Database()
    appointments = await db.appointments.find({"salon_id": salon_id}).to_list(length=None)
    return [Appointment(**appointment) for appointment in appointments]

async def get_expert_appointments(expert_id: str) -> List[Appointment]:
    db = Database()
    appointments = await db.appointments.find({"expert_id": expert_id}).to_list(length=None)
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
        appointment = await get_appointment(appointment_id)
        if appointment:
            # Get user's phone number
            user = await db.users.find_one({"user_id": appointment.user_id})
            if user and user.get("phone_number"):
                # Get service and salon details
                service = await db.services.find_one({"service_id": appointment.service_id})
                salon = await db.salons.find_one({"salon_id": appointment.salon_id})
                expert = await db.experts.find_one({"expert_id": appointment.expert_id})
                
                # Send confirmation message
                twilio_service = TwilioService()
                
                appointment_details = {
                    "service_name": service.get("name", "Unknown Service") if service else "Unknown Service",
                    "salon_name": salon.get("name", "Unknown Salon") if salon else "Unknown Salon",
                    "expert_name": expert.get("name", "Unknown Expert") if expert else "Unknown Expert",
                    "date": appointment.appointment_date.strftime("%Y-%m-%d"),
                    "time": appointment.appointment_time
                }
                
                await twilio_service.send_appointment_confirmation(
                    user["phone_number"],
                    appointment_details
                )
        return appointment
    return None

async def get_upcoming_appointments(user_id: str) -> List[Appointment]:
    db = Database()
    current_time = datetime.utcnow()
    appointments = await db.appointments.find({
        "user_id": user_id,
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
    
    if appointment.expert_id != expert_id:
        raise HTTPException(status_code=403, detail="Not authorized to confirm this appointment")
    
    update_result = await db.appointments.update_one(
        {"appointment_id": appointment_id},
        {"$set": {"expert_confirmed": True}}
    )
    
    if update_result.modified_count:
        # Send notification to user
        notification_service = NotificationService(db)
        await notification_service.send_appointment_status_notification(
            user_id=appointment.user_id,
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
            # Get updated appointment
            updated_appointment = await db.appointments.find_one({"appointment_id": appointment_id})
            print(f"[DEBUG] Updated appointment: {updated_appointment}")
            
            # Get user's phone number
            user = await db.users.find_one({"user_id": appointment["user_id"]})
            print(f"[DEBUG] Found user: {user}")
            
            if user and "phone_number" in user:
                # Set up review state before sending the review request
                if booking_service:
                    print(f"[DEBUG] Setting up review state for phone: {user['phone_number']}")
                    await booking_service._setup_review_state(user["phone_number"], appointment_id)
                
                # Send review request
                print("[DEBUG] Sending review request message")
                twilio_service = TwilioService()
                await twilio_service.send_sms(
                    user["phone_number"],
                    "Thank you for visiting us! We'd love to hear your feedback.\n\n"
                    "Please rate your experience on a scale of 1-5 (5 being the best) "
                    "and include any comments you have.\n\n"
                    "Example: 5 - Great service, very professional!"
                )
                print("[DEBUG] Review request message sent")
            
            return Appointment(**updated_appointment)
        return None
        
    except Exception as e:
        print(f"[DEBUG] Error in complete_appointment: {str(e)}")
        logging.error(f"Error completing appointment: {str(e)}", exc_info=True)
        raise

async def handle_review_response(appointment_id: str, review_message: str) -> Optional[Appointment]:
    """Handle user's review response for a completed appointment"""
    try:
        print(f"\n[DEBUG] Starting handle_review_response for appointment_id: {appointment_id}")
        print(f"[DEBUG] Review message: {review_message}")
        
        db = Database()
        
        # Get the appointment
        appointment = await db.appointments.find_one({"appointment_id": appointment_id})
        if not appointment:
            print("[DEBUG] Appointment not found")
            return None
            
        print(f"[DEBUG] Found appointment: {appointment}")
            
        # Get user's phone number
        user = await db.users.find_one({"user_id": appointment["user_id"]})
        if not user or "phone_number" not in user:
            print("[DEBUG] User not found or no phone number")
            return None

        print(f"[DEBUG] Found user: {user}")
        twilio_service = TwilioService()
        
        try:
            # Parse message - handle both formats:
            # 1. Just rating: "5"
            # 2. Rating with comment: "5 - Great service" or "5-Great service"
            rating = None
            comment = ""
            
            print("[DEBUG] Attempting to parse review message")
            
            # First try to parse as just a number
            try:
                rating = int(review_message.strip())
                if rating < 1 or rating > 5:
                    raise ValueError("Rating must be between 1 and 5")
                print(f"[DEBUG] Parsed rating as number: {rating}")
            except ValueError:
                # If not a number, try to parse as "rating - comment" format
                print("[DEBUG] Not a number, trying to parse as 'rating - comment' format")
                parts = review_message.replace(" - ", "-").split('-', 1)
                if len(parts) >= 1:
                    try:
                        rating = int(parts[0].strip())
                        if rating < 1 or rating > 5:
                            raise ValueError("Rating must be between 1 and 5")
                        if len(parts) == 2:
                            comment = parts[1].strip()
                        print(f"[DEBUG] Parsed rating: {rating}, comment: {comment}")
                    except ValueError:
                        print("[DEBUG] Failed to parse rating from parts")
                        await twilio_service.send_sms(
                            user["phone_number"],
                            "Please provide a rating between 1-5, followed by your comments (optional)."
                        )
                        return None

            if rating is None:
                print("[DEBUG] Rating is None after parsing attempts")
                await twilio_service.send_sms(
                    user["phone_number"],
                    "Please provide a rating between 1-5, followed by your comments (optional)."
                )
                return None

            # Update the salon rating
            try:
                print(f"[DEBUG] Calling add_rating with salon_id: {appointment['salon_id']}, user_id: {appointment['user_id']}, rating: {rating}")
                await add_rating(
                    salon_id=appointment["salon_id"],
                    user_id=appointment["user_id"],
                    rating=rating,
                    comment=comment
                )
                print("[DEBUG] Successfully updated rating")
                
                # Send thank you message
                await twilio_service.send_sms(
                    user["phone_number"],
                    "Thank you for your feedback! We appreciate your input. 😊\n\nSend 'hi' to book another service."
                )
                print("[DEBUG] Thank you message sent")
            except Exception as e:
                print(f"[DEBUG] Error updating salon rating: {str(e)}")
                logging.error(f"Error updating salon rating: {str(e)}")
                await twilio_service.send_sms(
                    user["phone_number"],
                    "Sorry, there was an error saving your feedback."
                )
        except Exception as e:
            print(f"[DEBUG] Error handling review response: {str(e)}")
            logging.error(f"Error handling review response: {str(e)}", exc_info=True)
            await twilio_service.send_sms(
                user["phone_number"],
                "Sorry, something went wrong processing your feedback."
            )
        
        return Appointment(**appointment)
        
    except Exception as e:
        print(f"[DEBUG] Error in handle_review_response: {str(e)}")
        logging.error(f"Error handling review response: {str(e)}", exc_info=True)
        raise 