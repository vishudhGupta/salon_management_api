from typing import List, Optional
from schemas.appointment import AppointmentCreate, Appointment, generate_appointment_id
from config.database import Database
from datetime import datetime
from fastapi import HTTPException
from services.notification_service import NotificationService
import logging

async def check_expert_availability(expert_id: str, appointment_date: datetime, appointment_time: str) -> bool:
    """Check if expert is available at the given date and time"""
    # Convert appointment_time to datetime for comparison
    time_parts = appointment_time.split(":")
    appointment_datetime = appointment_date.replace(
        hour=int(time_parts[0]),
        minute=int(time_parts[1])
    )
    
    # Check for existing appointments
    db = Database()
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

        # Validate expert
        if appointment.expert_id:
            expert = await db.experts.find_one({
                "expert_id": appointment.expert_id,
                "salon_id": appointment.salon_id
            })
            if not expert:
                raise ValueError(f"Expert with ID {appointment.expert_id} not found in salon {appointment.salon_id}")

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
            # Update user's appointments array
            await db.users.update_one(
                {"user_id": appointment.user_id},
                {"$addToSet": {"appointments": appointment_id}}
            )
            
            # Update salon's appointments array
            await db.salons.update_one(
                {"salon_id": appointment.salon_id},
                {"$addToSet": {"appointments": appointment_id}}
            )
            
            # Update expert's appointments array if provided
            if appointment.expert_id:
                await db.experts.update_one(
                    {"expert_id": appointment.expert_id},
                    {"$addToSet": {"appointments": appointment_id}}
                )
                
        except Exception as e:
            # If updating references fails, try to clean up the appointment
            logging.error(f"Error updating references for appointment {appointment_id}: {str(e)}")
            try:
                await db.appointments.delete_one({"appointment_id": appointment_id})
            except:
                pass
            raise
            
        # Return the created appointment
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
        return await get_appointment(appointment_id)
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