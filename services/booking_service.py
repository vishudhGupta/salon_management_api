from datetime import datetime, timedelta
from typing import Optional, List, Dict
from services.twilio_service import TwilioService
from crud.user_crud import get_user_by_phone, create_user, update_user, get_user
from crud.salon_crud import get_salon, update_salon, get_all_salons, get_salon_services, get_salon_experts
from crud.service_crud import get_service, get_all_services
from crud.expert_crud import get_expert
from crud.appointment_crud import create_appointment, update_appointment, get_appointment
from schemas.user import UserCreate
from schemas.salon import Appointment
from schemas.appointment import AppointmentCreate
from config.database import Database
import re

class BookingService:
    def __init__(self):
        self.twilio_service = TwilioService()
        self.user_states: Dict[str, Dict] = {}  # phone_number -> state data
        self.retry_counts: Dict[str, int] = {}  # phone_number -> retry count
        self.db = Database()

    async def _handle_registration_state(self, phone_number: str, message: str) -> Dict:
        state = self.user_states.get(phone_number, {})
        registration_data = state.get("registration_data", {})
        step = state.get("registration_step", "name")

        if step == "name":
            registration_data["name"] = message.strip()
            self.user_states[phone_number].update({
                "registration_step": "email",
                "registration_data": registration_data
            })
            await self.twilio_service.send_sms(phone_number, "Please enter your email:")
            return {"status": "awaiting_email"}
        
        elif step == "email":
            registration_data["email"] = message.strip()
            self.user_states[phone_number].update({
                "registration_step": "address",
                "registration_data": registration_data
            })
            await self.twilio_service.send_sms(phone_number, "Please enter your address:")
            return {"status": "awaiting_address"}

        elif step == "address":
            registration_data["address"] = message.strip()
            self.user_states[phone_number].update({
                "registration_step": "password",
                "registration_data": registration_data
            })
            await self.twilio_service.send_sms(phone_number, "Please enter a password (minimum 8 characters):")
            return {"status": "awaiting_password"}

        elif step == "password":
            if len(message.strip()) < 8:
                await self.twilio_service.send_sms(phone_number, "❌ Password too short. Please enter at least 8 characters:")
                return {"status": "invalid_password"}

            registration_data["password"] = message.strip()

            try:
                user = UserCreate(
                    name=registration_data["name"],
                    email=registration_data["email"],
                    phone_number=phone_number,
                    address=registration_data["address"],
                    password=registration_data["password"]
                )
                new_user = await create_user(user)

                self.user_states[phone_number] = {
                    "state": "salon_selection",
                    "user_id": new_user.user_id,
                    "last_message_time": datetime.now()
                }

                await self.twilio_service.send_sms(phone_number, f"🎉 Registration successful! Welcome {user.name}!")
                return await self._show_salons(phone_number)

            except Exception as e:
                await self.twilio_service.send_sms(phone_number, "⚠️ Registration failed. Please try again later.")
                self._reset_user_state(phone_number)
                return {"status": "error", "message": str(e)}

        else:
            self._reset_user_state(phone_number)
            await self.twilio_service.send_sms(phone_number, "Something went wrong. Please type 'hi' to start again.")
            return {"status": "error", "message": "Unknown registration step"}


    

    def _reset_user_state(self, phone_number: str) -> None:
        """Reset user state and retry count"""
        if phone_number in self.user_states:
            del self.user_states[phone_number]
        if phone_number in self.retry_counts:
            del self.retry_counts[phone_number]

    def _validate_state_transition(self, current_state: str, next_state: str) -> bool:
        """Validate if the state transition is allowed"""
        valid_transitions = {
            "welcome": ["registration", "salon_selection"],
            "registration": ["salon_selection"],
            "salon_selection": ["service_selection"],
            "service_selection": ["expert_selection"],
            "expert_selection": ["date_selection"],
            "date_selection": ["time_selection"],
            "time_selection": ["confirmation"],
            "confirmation": ["salon_selection"]  # After confirmation, can start new booking
        }
        return next_state in valid_transitions.get(current_state, [])

    async def handle_incoming_message(self, phone_number: str, message: str) -> Dict:
        """Handle incoming WhatsApp message"""
        try:
            # Clean phone number (remove 'whatsapp:' prefix if present)
            phone_number = phone_number.replace('whatsapp:', '')
            
            # Handle initial greetings
            if message.lower() in ["hi", "hello", "hey", "start"]:
                self._reset_user_state(phone_number)
                # Initialize state before sending welcome message
                try:
                    user = await get_user_by_phone(phone_number)
                    if user:
                        self.user_states[phone_number] = {
                            "state": "welcome",
                            "user_id": user.user_id,
                            "last_message_time": datetime.now()
                        }
                    else:
                        self.user_states[phone_number] = {
                            "state": "welcome",
                            "last_message_time": datetime.now()
                        }
                except Exception as e:
                    self.user_states[phone_number] = {
                        "state": "welcome",
                        "last_message_time": datetime.now()
                    }
                
                await self.twilio_service.send_welcome_message(phone_number)
                return {"status": "success"}
            
            # Handle cancel command at any point
            if message.lower() == "cancel":
                self._reset_user_state(phone_number)
                await self.twilio_service.send_sms(phone_number, "Booking cancelled. Send 'hi' to start over.")
                return {"status": "success"}

            # Initialize state if not exists
            if phone_number not in self.user_states:
                self.user_states[phone_number] = {
                    "state": "welcome",
                    "last_message_time": datetime.now()
                }
                await self.twilio_service.send_welcome_message(phone_number)
                return {"status": "success"}

            # Check for session timeout (30 minutes)
            last_message_time = self.user_states[phone_number].get("last_message_time")
            if last_message_time and (datetime.now() - last_message_time) > timedelta(minutes=30):
                self._reset_user_state(phone_number)
                self.user_states[phone_number] = {
                    "state": "welcome",
                    "last_message_time": datetime.now()
                }
                await self.twilio_service.send_welcome_message(phone_number)
                return {"status": "success"}

            # Update last message time
            self.user_states[phone_number]["last_message_time"] = datetime.now()

            # Handle message based on current state
            state = self.user_states[phone_number]["state"]

            if state == "welcome":
                if message.upper() == "LOGIN":
                    try:
                        user = await get_user_by_phone(phone_number)
                        if not user:
                            self.user_states[phone_number]["state"] = "registration"
                            await self.twilio_service.send_registration_prompt(phone_number)
                        else:
                            self.user_states[phone_number].update({
                                "state": "salon_selection",
                                "user_id": user.user_id
                            })
                            return await self._show_salons(phone_number)
                    except Exception as e:
                        await self.twilio_service.send_sms(phone_number, "Error during login. Please try again by sending 'hi'.")
                        self._reset_user_state(phone_number)
                        return {"status": "error", "message": str(e)}
                elif message.upper() == "REGISTER":
                    self.user_states[phone_number]["state"] = "registration"
                    await self.twilio_service.send_registration_prompt(phone_number)
                else:
                    await self.twilio_service.send_welcome_message(phone_number)
                return {"status": "success"}

            # Process message based on state
            try:
                if state == "registration":
                    return await self._handle_registration_state(phone_number, message)
                elif state == "salon_selection":
                    return await self._handle_salon_selection_state(phone_number, message)
                elif state == "service_selection":
                    return await self._handle_service_selection_state(phone_number, message)
                elif state == "expert_selection":
                    return await self._handle_expert_selection_state(phone_number, message)
                elif state == "date_selection":
                    return await self._handle_date_selection_state(phone_number, message)
                elif state == "time_selection":
                    return await self._handle_time_selection_state(phone_number, message)
                elif state == "confirmation":
                    return await self._handle_confirmation_state(phone_number, message)
                elif state == "feedback":
                    return await self._handle_feedback_state(phone_number, message)
                else:
                    self._reset_user_state(phone_number)
                    await self.twilio_service.send_welcome_message(phone_number)
                    return {"status": "success"}
            except Exception as e:
                await self.twilio_service.send_sms(phone_number, f"Error processing your request. Please try again by sending 'hi'.")
                self._reset_user_state(phone_number)
                return {"status": "error", "message": str(e)}

        except Exception as e:
            self._reset_user_state(phone_number)
            await self.twilio_service.send_sms(phone_number, "Sorry, something went wrong. Please try again by sending 'hi'.")
            return {"status": "error", "message": str(e)}

    def _validate_input(self, state: str, message: str) -> bool:
        """Validate input based on current state"""
        try:
            if state == "registration":
                # Check if message contains required registration fields
                required_fields = ["name:", "email:", "address:", "password:"]
                return all(field.lower() in message.lower() for field in required_fields)
            elif state in ["salon_selection", "service_selection", "expert_selection"]:
                # Validate numeric input
                num = int(message.strip())
                return num > 0
            elif state == "date_selection":
                # Validate date format (YYYY-MM-DD)
                datetime.strptime(message.strip(), "%Y-%m-%d")
                return True
            elif state == "time_selection":
                # Validate time format (HH:MM)
                datetime.strptime(message.strip(), "%H:%M")
                return True
            elif state == "confirmation":
                return message.lower() in ["confirm", "cancel"]
            return True
        except (ValueError, TypeError):
            return False

    def _get_input_instructions(self, state: str) -> str:
        """Get input instructions based on current state"""
        instructions = {
            "registration": "Please provide your details in the format:\nName: [Your Name]\nEmail: [Your Email]\nAddress: [Your Address]\nPassword: [Your Password]",
            "salon_selection": "Please enter the number of your chosen salon.",
            "service_selection": "Please enter the number of your chosen service.",
            "expert_selection": "Please enter the number of your chosen expert.",
            "date_selection": "Please enter the date in YYYY-MM-DD format.",
            "time_selection": "Please enter the time in HH:MM format.",
            "confirmation": "Please type 'confirm' to proceed or 'cancel' to start over."
        }
        return instructions.get(state, "Please send 'hi' to start over.")

    def _increment_retry(self, phone_number: str) -> bool:
        """Increment retry count and return True if max retries reached"""
        if phone_number not in self.retry_counts:
            self.retry_counts[phone_number] = 0
        self.retry_counts[phone_number] += 1
        return self.retry_counts[phone_number] >= 3

    async def _start_registration(self, phone_number: str) -> Dict:
        """Start the registration process"""
        message = (
            "Welcome! Let's get you registered. Please provide your details in the following format:\n\n"
            "Name: [Your Name]\n"
            "Email: [Your Email]\n"
            "Address: [Your Address]\n"
            "Password: [Your Password]"
        )
        await self.twilio_service.send_sms(phone_number, message)
        return {"status": "success"}
    
    async def _handle_registration_state(self, phone_number: str, message: str) -> Dict:
        state = self.user_states.get(phone_number, {})
        registration_data = state.get("registration_data", {})
        step = state.get("registration_step", "name")

        if step == "name":
            registration_data["name"] = message.strip()
            self.user_states[phone_number].update({
                "registration_step": "email",
                "registration_data": registration_data
            })
            await self.twilio_service.send_sms(phone_number, "Please enter your email:")
            return {"status": "awaiting_email"}
        
        elif step == "email":
            registration_data["email"] = message.strip()
            self.user_states[phone_number].update({
                "registration_step": "address",
                "registration_data": registration_data
            })
            await self.twilio_service.send_sms(phone_number, "Please enter your address:")
            return {"status": "awaiting_address"}

        elif step == "address":
            registration_data["address"] = message.strip()
            self.user_states[phone_number].update({
                "registration_step": "password",
                "registration_data": registration_data
            })
            await self.twilio_service.send_sms(phone_number, "Please enter a password (minimum 8 characters):")
            return {"status": "awaiting_password"}

        elif step == "password":
            if len(message.strip()) < 8:
                await self.twilio_service.send_sms(phone_number, "❌ Password too short. Please enter at least 8 characters:")
                return {"status": "invalid_password"}

            registration_data["password"] = message.strip()

            try:
                user = UserCreate(
                    name=registration_data["name"],
                    email=registration_data["email"],
                    phone_number=phone_number,
                    address=registration_data["address"],
                    password=registration_data["password"]
                )
                new_user = await create_user(user)

                self.user_states[phone_number] = {
                    "state": "salon_selection",
                    "user_id": new_user.user_id,
                    "last_message_time": datetime.now()
                }

                await self.twilio_service.send_sms(phone_number, f"🎉 Registration successful! Welcome {user.name}!")
                return await self._show_salons(phone_number)

            except Exception as e:
                await self.twilio_service.send_sms(phone_number, "⚠️ Registration failed. Please try again later.")
                self._reset_user_state(phone_number)
                return {"status": "error", "message": str(e)}

        else:
            self._reset_user_state(phone_number)
            await self.twilio_service.send_sms(phone_number, "Something went wrong. Please type 'hi' to start again.")
            return {"status": "error", "message": "Unknown registration step"}


    

    async def _show_salons(self, phone_number: str) -> Dict:
        try:
            salons = await get_all_salons()
            if not salons:
                await self.twilio_service.send_sms(phone_number, "No salons are available at the moment.")
                return {"status": "error", "message": "No salons available"}

            self.user_states[phone_number]["salons"] = salons

            # Build WhatsApp list section
            message = "Please select a salon by typing its number:\n\n"
            for i, salon in enumerate(salons, 1):
                message += f"{i}. {salon.name} - {salon.address}\n"
            await self.twilio_service.send_sms(phone_number, message)

            return {"status": "success"}

        except Exception as e:
            await self.twilio_service.send_sms(phone_number, "Something went wrong. Please type 'hi' to start again.")
            self._reset_user_state(phone_number)
            return {"status": "error", "message": str(e)}


    async def _handle_salon_selection_state(self, phone_number: str, message: str) -> Dict:
        """Handle salon selection by the user"""
        try:
            salon_index = int(message.strip()) -1
            salons = self.user_states[phone_number].get("salons", [])
            
            if not salons:
                return await self._show_salons(phone_number)
            
            if 0 <= salon_index < len(salons):
                selected_salon = salons[salon_index]
                # Validate state transition
                if not self._validate_state_transition(self.user_states[phone_number]["state"], "service_selection"):
                    self._reset_user_state(phone_number)
                    error_msg = "Invalid state transition. Please try again by sending 'hi'."
                    await self.twilio_service.send_sms(phone_number, error_msg)
                    return {"status": "error", "message": "Invalid state transition"}
                
                self.user_states[phone_number].update({
                    "state": "service_selection",
                    "selected_salon": selected_salon
                })
                return await self._show_services(phone_number)
            else:
                if self._increment_retry(phone_number):
                    self._reset_user_state(phone_number)
                    error_msg = "Too many invalid attempts. Please start over by sending 'hi'."
                    await self.twilio_service.send_sms(phone_number, error_msg)
                    return {"status": "error", "message": "Too many retries"}
                
                error_msg = "Invalid selection. Please choose a number from the list."
                await self.twilio_service.send_sms(phone_number, error_msg)
                return {"status": "error", "message": "Invalid selection"}
        except ValueError:
            if self._increment_retry(phone_number):
                self._reset_user_state(phone_number)
                error_msg = "Too many invalid attempts. Please start over by sending 'hi'."
                await self.twilio_service.send_sms(phone_number, error_msg)
                return {"status": "error", "message": "Too many retries"}
            
            error_msg = "Please enter a valid number."
            await self.twilio_service.send_sms(phone_number, error_msg)
            return {"status": "error", "message": "Invalid number format"}
        except Exception as e:
            error_msg = "Sorry, we're having trouble with your salon selection. Please try again by sending 'hi'."
            await self.twilio_service.send_sms(phone_number, error_msg)
            self._reset_user_state(phone_number)
            return {"status": "error", "message": str(e)}

    async def _show_services(self, phone_number: str) -> Dict:
        """Show available services for the selected salon"""
        try:
            salon = self.user_states[phone_number]["selected_salon"]
            service_ids = await get_salon_services(salon.salon_id)
            
            if not service_ids:
                message = "No services available at this salon. Please select another salon by sending 'hi'."
                await self.twilio_service.send_sms(phone_number, message)
                self._reset_user_state(phone_number)
                return {"status": "error", "message": "No services available"}

            # Store service IDs in user state
            self.user_states[phone_number]["services"] = []
            
            # Format service list message
            message = "Please select a service by typing its number:\n\n"
            for i, service_id in enumerate(service_ids, 1):
                try:
                    service = await get_service(service_id)
                    if service:
                        self.user_states[phone_number]["services"].append(service)
                        message += f"{i}. {service.name} - ${service.cost} ({service.duration} mins)\n"
                except Exception as e:
                    continue
            
            if not self.user_states[phone_number]["services"]:
                message = "Error loading services. Please try again by sending 'hi'."
                await self.twilio_service.send_sms(phone_number, message)
                self._reset_user_state(phone_number)
                return {"status": "error", "message": "Error loading services"}

            # Send service list
            await self.twilio_service.send_sms(phone_number, message)
            return {"status": "success"}
        except Exception as e:
            error_msg = "Sorry, we're having trouble fetching the service list. Please try again by sending 'hi'."
            await self.twilio_service.send_sms(phone_number, error_msg)
            self._reset_user_state(phone_number)
            return {"status": "error", "message": str(e)}

    async def _handle_service_selection_state(self, phone_number: str, message: str) -> Dict:
        try:
            service_index = int(message.strip()) - 1
            services = self.user_states[phone_number].get("services", [])
            
            if not services:
                return await self._show_services(phone_number)
            
            if 0 <= service_index < len(services):
                selected_service = services[service_index]
                # Validate state transition
                if not self._validate_state_transition(self.user_states[phone_number]["state"], "expert_selection"):
                    self._reset_user_state(phone_number)
                    return {"message": "Invalid state transition. Please send 'hi' to start over."}
                
                self.user_states[phone_number].update({
                    "state": "expert_selection",
                    "selected_service": selected_service
                })
                return await self._show_experts(phone_number)
            else:
                if self._increment_retry(phone_number):
                    return await self._show_services(phone_number)
                return {"message": "Invalid selection. Please choose a number from the list."}
        except (ValueError, KeyError):
            if self._increment_retry(phone_number):
                return await self._show_services(phone_number)
            return {"message": "Please enter a valid number."}

    async def _show_experts(self, phone_number: str) -> Dict:
        """Show available experts for the selected salon"""
        try:
            salon = self.user_states[phone_number]["selected_salon"]
            expert_ids = await get_salon_experts(salon.salon_id)
            
            if not expert_ids:
                message = "No experts available at this salon. Please select another salon by sending 'hi'."
                await self.twilio_service.send_sms(phone_number, message)
                self._reset_user_state(phone_number)
                return {"status": "error", "message": "No experts available"}

            # Store experts in user state
            self.user_states[phone_number]["experts"] = []
            
            # Format expert list message - Simple list with only expert names
            message = "Please select an expert by typing its number:\n\n"
            for i, expert_id in enumerate(expert_ids, 1):
                try:
                    expert = await get_expert(expert_id)
                    if expert:
                        self.user_states[phone_number]["experts"].append(expert)
                        # Simplified display - just the name
                        message += f"{i}. {expert.name}\n"
                except Exception as e:
                    continue
            
            if not self.user_states[phone_number]["experts"]:
                message = "Error loading experts. Please try again by sending 'hi'."
                await self.twilio_service.send_sms(phone_number, message)
                self._reset_user_state(phone_number)
                return {"status": "error", "message": "Error loading experts"}

            # Send expert list
            await self.twilio_service.send_sms(phone_number, message)
            return {"status": "success"}
        except Exception as e:
            error_msg = "Sorry, we're having trouble fetching the expert list. Please try again by sending 'hi'."
            await self.twilio_service.send_sms(phone_number, error_msg)
            self._reset_user_state(phone_number)
            return {"status": "error", "message": str(e)}

    async def _handle_expert_selection_state(self, phone_number: str, message: str) -> Dict:
        try:
            expert_index = int(message.strip()) - 1
            experts = self.user_states[phone_number].get("experts", [])
            
            if not experts:
                return await self._show_experts(phone_number)
            
            if 0 <= expert_index < len(experts):
                selected_expert = experts[expert_index]
                # Validate state transition
                if not self._validate_state_transition(self.user_states[phone_number]["state"], "date_selection"):
                    self._reset_user_state(phone_number)
                    return {"message": "Invalid state transition. Please send 'hi' to start over."}
                
                self.user_states[phone_number].update({
                    "state": "date_selection",
                    "selected_expert": selected_expert
                })
                return await self._show_available_dates(phone_number)
            else:
                if self._increment_retry(phone_number):
                    return await self._show_experts(phone_number)
                return {"message": "Invalid selection. Please choose a number from the list."}
        except (ValueError, KeyError):
            if self._increment_retry(phone_number):
                return await self._show_experts(phone_number)
            return {"message": "Please enter a valid number."}

    async def _show_available_dates(self, phone_number: str) -> Dict:
        """Show available dates for booking"""
        try:
            # Get dates for the next 7 days
            dates = []
            for i in range(7):
                date = datetime.now() + timedelta(days=i+1)
                dates.append(date.strftime("%Y-%m-%d"))

            message = "Please select a date by typing its number:\n\n"
            for i, date in enumerate(dates, 1):
                message += f"{i}. {date}\n"

            self.user_states[phone_number]["available_dates"] = dates
            await self.twilio_service.send_sms(phone_number, message)
            return {"status": "success"}
        except Exception as e:
            error_msg = "Sorry, we're having trouble with date selection. Please try again by sending 'hi'."
            await self.twilio_service.send_sms(phone_number, error_msg)
            self._reset_user_state(phone_number)
            return {"status": "error", "message": str(e)}

    async def _handle_date_selection_state(self, phone_number: str, message: str) -> Dict:
        try:
            date_index = int(message.strip()) - 1
            dates = self.user_states[phone_number].get("available_dates", [])
            
            if not dates:
                return await self._show_available_dates(phone_number)
            
            if 0 <= date_index < len(dates):
                selected_date = dates[date_index]
                # Validate state transition
                if not self._validate_state_transition(self.user_states[phone_number]["state"], "time_selection"):
                    self._reset_user_state(phone_number)
                    error_msg = "Invalid state transition. Please try again by sending 'hi'."
                    await self.twilio_service.send_sms(phone_number, error_msg)
                    return {"status": "error", "message": "Invalid state transition"}
                
                self.user_states[phone_number].update({
                    "state": "time_selection",
                    "selected_date": selected_date
                })
                return await self._show_available_times(phone_number)
            else:
                if self._increment_retry(phone_number):
                    self._reset_user_state(phone_number)
                    error_msg = "Too many invalid attempts. Please start over by sending 'hi'."
                    await self.twilio_service.send_sms(phone_number, error_msg)
                    return {"status": "error", "message": "Too many retries"}
                
                error_msg = "Invalid selection. Please choose a number from the list."
                await self.twilio_service.send_sms(phone_number, error_msg)
                return {"status": "error", "message": "Invalid selection"}
        except ValueError:
            if self._increment_retry(phone_number):
                self._reset_user_state(phone_number)
                error_msg = "Too many invalid attempts. Please start over by sending 'hi'."
                await self.twilio_service.send_sms(phone_number, error_msg)
                return {"status": "error", "message": "Too many retries"}
            
            error_msg = "Please enter a valid number."
            await self.twilio_service.send_sms(phone_number, error_msg)
            return {"status": "error", "message": "Invalid number format"}
        except Exception as e:
            error_msg = "Sorry, something went wrong with your date selection. Please try again by sending 'hi'."
            await self.twilio_service.send_sms(phone_number, error_msg)
            self._reset_user_state(phone_number)
            return {"status": "error", "message": str(e)}

    async def _show_available_times(self, phone_number: str) -> Dict:
        """Show available time slots for the selected date"""
        try:
            # Generate time slots from 9 AM to 5 PM
            time_slots = []
            for hour in range(9, 17):
                time_slots.append(f"{hour:02d}:00")
                time_slots.append(f"{hour:02d}:30")

            message = "Please select a time slot by typing its number:\n\n"
            for i, time in enumerate(time_slots, 1):
                message += f"{i}. {time}\n"

            self.user_states[phone_number]["available_times"] = time_slots
            await self.twilio_service.send_sms(phone_number, message)
            return {"status": "success"}
        except Exception as e:
            error_msg = "Sorry, we're having trouble with time selection. Please try again by sending 'hi'."
            await self.twilio_service.send_sms(phone_number, error_msg)
            self._reset_user_state(phone_number)
            return {"status": "error", "message": str(e)}

    async def _handle_time_selection_state(self, phone_number: str, message: str) -> Dict:
        try:
            time_index = int(message.strip()) - 1
            times = self.user_states[phone_number].get("available_times", [])
            
            if not times:
                return await self._show_available_times(phone_number)
            
            if 0 <= time_index < len(times):
                selected_time = times[time_index]
                # Validate state transition
                if not self._validate_state_transition(self.user_states[phone_number]["state"], "confirmation"):
                    self._reset_user_state(phone_number)
                    error_msg = "Invalid state transition. Please try again by sending 'hi'."
                    await self.twilio_service.send_sms(phone_number, error_msg)
                    return {"status": "error", "message": "Invalid state transition"}
                
                self.user_states[phone_number].update({
                    "state": "confirmation",
                    "selected_time": selected_time
                })
                return await self._show_confirmation(phone_number)
            else:
                if self._increment_retry(phone_number):
                    self._reset_user_state(phone_number)
                    error_msg = "Too many invalid attempts. Please start over by sending 'hi'."
                    await self.twilio_service.send_sms(phone_number, error_msg)
                    return {"status": "error", "message": "Too many retries"}
                
                error_msg = "Invalid selection. Please choose a number from the list."
                await self.twilio_service.send_sms(phone_number, error_msg)
                return {"status": "error", "message": "Invalid selection"}
        except ValueError:
            if self._increment_retry(phone_number):
                self._reset_user_state(phone_number)
                error_msg = "Too many invalid attempts. Please start over by sending 'hi'."
                await self.twilio_service.send_sms(phone_number, error_msg)
                return {"status": "error", "message": "Too many retries"}
            
            error_msg = "Please enter a valid number."
            await self.twilio_service.send_sms(phone_number, error_msg)
            return {"status": "error", "message": "Invalid number format"}
        except Exception as e:
            error_msg = "Sorry, something went wrong with your time selection. Please try again by sending 'hi'."
            await self.twilio_service.send_sms(phone_number, error_msg)
            self._reset_user_state(phone_number)
            return {"status": "error", "message": str(e)}

    async def _show_confirmation(self, phone_number: str) -> Dict:
        """Show booking confirmation details"""
        try:
            state = self.user_states[phone_number]
            salon = state["selected_salon"]
            service = state["selected_service"]
            expert = state["selected_expert"]
            date = state["selected_date"]
            time = state["selected_time"]

            message = f"Please confirm your booking:\n\n" \
                     f"Salon: {salon.name}\n" \
                     f"Service: {service.name}\n" \
                     f"Expert: {expert.name}\n" \
                     f"Date: {date}\n" \
                     f"Time: {time}\n\n" \
                     f"Type 'confirm' to proceed or 'cancel' to start over."

            await self.twilio_service.send_sms(phone_number, message)
            return {"status": "success"}
        except Exception as e:
            error_msg = "Sorry, we're having trouble confirming your booking. Please try again by sending 'hi'."
            await self.twilio_service.send_sms(phone_number, error_msg)
            self._reset_user_state(phone_number)
            return {"status": "error", "message": str(e)}

    async def _handle_confirmation_state(self, phone_number: str, message: str) -> Dict:
        try:
            message = message.lower().strip()
            if message == "confirm":
                try:
                    state = self.user_states[phone_number]
                    
                    # Parse date and time
                    date_str = state['selected_date']
                    time_str = state['selected_time']
                    
                    try:
                        # Create appointment data
                        appointment_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                        
                        # Create appointment
                        appointment = AppointmentCreate(
                            user_id=state["user_id"],
                            salon_id=state["selected_salon"].salon_id,
                            service_id=state["selected_service"].service_id,
                            expert_id=state["selected_expert"].expert_id,
                            appointment_date=appointment_date,
                            appointment_time=time_str
                        )
                        
                        # Save to database
                        created_appointment = await create_appointment(appointment)
                        
                        # Send confirmation
                        confirmation_message = (
                            f"✅ Booking confirmed!\n\n"
                            f"Salon: {state['selected_salon'].name}\n"
                            f"Service: {state['selected_service'].name}\n"
                            f"Expert: {state['selected_expert'].name}\n"
                            f"Date: {date_str}\n"
                            f"Time: {time_str}\n\n"
                            f"We'll send you a reminder before your appointment."
                        )
                        
                        await self.twilio_service.send_sms(phone_number, confirmation_message)
                        self._reset_user_state(phone_number)
                        return {"status": "success", "message": "Booking confirmed"}
                        
                    except Exception as e:
                        error_msg = "Sorry, there was an error creating your appointment. Please try again by sending 'hi'."
                        await self.twilio_service.send_sms(phone_number, error_msg)
                        self._reset_user_state(phone_number)
                        return {"status": "error", "message": str(e)}
                    
                except Exception as e:
                    error_msg = "Sorry, something went wrong with your booking. Please try again by sending 'hi'."
                    await self.twilio_service.send_sms(phone_number, error_msg)
                    self._reset_user_state(phone_number)
                    return {"status": "error", "message": str(e)}
            elif message == "cancel":
                # Reset the state
                self._reset_user_state(phone_number)
                await self.twilio_service.send_sms(phone_number, "Booking cancelled. Send 'hi' to start over.")
                return {"status": "success", "message": "Booking cancelled"}
            else:
                if self._increment_retry(phone_number):
                    self._reset_user_state(phone_number)
                    error_msg = "Too many invalid attempts. Please start over by sending 'hi'."
                    await self.twilio_service.send_sms(phone_number, error_msg)
                    return {"status": "error", "message": "Too many retries"}
                
                error_msg = "Please type 'confirm' to proceed or 'cancel' to start over."
                await self.twilio_service.send_sms(phone_number, error_msg)
                return {"status": "error", "message": "Invalid confirmation response"}
        except Exception as e:
            error_msg = "Sorry, something went wrong with your confirmation. Please try again by sending 'hi'."
            await self.twilio_service.send_sms(phone_number, error_msg)
            self._reset_user_state(phone_number)
            return {"status": "error", "message": str(e)}

    async def _schedule_reminders(self, appointment: Appointment) -> None:
        # Schedule 24-hour reminder
        reminder_time_24h = appointment.appointment_date - timedelta(hours=24)
        if reminder_time_24h > datetime.utcnow():
            # You might want to use a proper task queue here
            await self._send_reminder(appointment, 24)
        
        # Schedule 1-hour reminder
        reminder_time_1h = appointment.appointment_date - timedelta(hours=1)
        if reminder_time_1h > datetime.utcnow():
            # You might want to use a proper task queue here
            await self._send_reminder(appointment, 1)

    async def _send_reminder(self, appointment: Appointment, hours_before: int) -> None:
        user = await get_user(appointment.user_id)
        await self.twilio_service.send_appointment_reminder(
            user.phone_number,
            {
                "service_name": (await get_service(appointment.service_id)).name,
                "salon_name": (await get_salon(appointment.salon_id)).name,
                "expert_name": (await get_expert(appointment.expert_id)).name,
                "date": appointment.appointment_date.strftime("%Y-%m-%d"),
                "time": appointment.appointment_time
            },
            hours_before
        )

    async def _request_feedback(self, phone_number: str, appointment_id: str) -> Dict:
        """Request feedback from customer after appointment"""
        try:
            # First check if appointment exists and is completed
            appointment = await get_appointment(appointment_id)
            if not appointment or appointment.status != "completed":
                return {"status": "error", "message": "Appointment not found or not completed"}
            
            # Set up feedback collection state
            self.user_states[phone_number] = {
                "state": "feedback",
                "appointment_id": appointment_id,
                "last_message_time": datetime.now()
            }
            
            # Send feedback request
            message = (
                "Thank you for visiting us! We'd love to hear your feedback.\n\n"
                "Please rate your experience on a scale of 1-5 (5 being the best) "
                "and include any comments you have.\n\n"
                "Example: 5 - Great service, very professional!"
            )
            await self.twilio_service.send_sms(phone_number, message)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_feedback_state(self, phone_number: str, message: str) -> Dict:
        """Handle feedback from customer"""
        try:
            # Try to parse rating from message (format: rating - comment)
            parts = message.split('-', 1)
            rating = None
            comment = ""
            
            if len(parts) >= 1:
                try:
                    rating = int(parts[0].strip())
                    if rating < 1 or rating > 5:
                        raise ValueError("Rating must be between 1 and 5")
                except ValueError:
                    if self._increment_retry(phone_number):
                        self._reset_user_state(phone_number)
                        error_msg = "Too many invalid attempts. Thank you for your time."
                        await self.twilio_service.send_sms(phone_number, error_msg)
                        return {"status": "error", "message": "Too many retries"}
                    
                    error_msg = "Please provide a rating between 1-5, followed by your comments."
                    await self.twilio_service.send_sms(phone_number, error_msg)
                    return {"status": "error", "message": "Invalid rating format"}
            
            if len(parts) >= 2:
                comment = parts[1].strip()
            
            # Get appointment ID from state
            appointment_id = self.user_states[phone_number].get("appointment_id")
            if not appointment_id:
                error_msg = "Sorry, we couldn't process your feedback. Please try again later."
                await self.twilio_service.send_sms(phone_number, error_msg)
                self._reset_user_state(phone_number)
                return {"status": "error", "message": "No appointment ID in state"}
            
            # Save rating to database
            try:
                appointment = await get_appointment(appointment_id)
                if appointment:
                    # Create rating object
                    rating_obj = {
                        "appointment_id": appointment_id,
                        "user_id": appointment.user_id,
                        "salon_id": appointment.salon_id,
                        "rating": rating,
                        "comment": comment,
                        "created_at": datetime.now()
                    }
                    
                    # Save rating to database
                    await self.db.ratings.insert_one(rating_obj)
                    
                    # Update salon's average rating
                    await self.update_salon_rating(appointment.salon_id)
                    
                    # Thank the user
                    thank_msg = "Thank you for your feedback! We appreciate your input."
                    await self.twilio_service.send_sms(phone_number, thank_msg)
                    self._reset_user_state(phone_number)
                    return {"status": "success"}
                else:
                    error_msg = "Sorry, we couldn't find your appointment. Please try again later."
                    await self.twilio_service.send_sms(phone_number, error_msg)
                    self._reset_user_state(phone_number)
                    return {"status": "error", "message": "Appointment not found"}
            except Exception as e:
                error_msg = "Sorry, we couldn't save your feedback. Please try again later."
                await self.twilio_service.send_sms(phone_number, error_msg)
                self._reset_user_state(phone_number)
                return {"status": "error", "message": str(e)}
        except Exception as e:
            error_msg = "Sorry, something went wrong processing your feedback. Please try again later."
            await self.twilio_service.send_sms(phone_number, error_msg)
            self._reset_user_state(phone_number)
            return {"status": "error", "message": str(e)}

    async def update_salon_rating(self, salon_id: str) -> None:
        """Update salon's average rating"""
        try:
            # Get all ratings for this salon
            ratings = await self.db.ratings.find({"salon_id": salon_id}).to_list(length=None)
            
            if ratings:
                # Calculate average
                total = sum(r.get("rating", 0) for r in ratings)
                average = total / len(ratings)
                
                # Update salon
                await self.db.salons.update_one(
                    {"salon_id": salon_id},
                    {"$set": {
                        "average_rating": round(average, 1),
                        "total_ratings": len(ratings)
                    }}
                )
        except Exception as e:
            pass 