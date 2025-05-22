from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from datetime import datetime, timedelta
from typing import Optional, List,Dict
import os
import re
from dotenv import load_dotenv

load_dotenv(override=True)

class TwilioService:
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER')
        
        if not all([self.account_sid, self.auth_token, self.whatsapp_number]):
            raise ValueError("Missing Twilio credentials")
            
        self.client = Client(self.account_sid, self.auth_token)

    def _format_phone_number(self, phone_number: str) -> str:
        """Format phone number to E.164 format and add WhatsApp prefix if needed."""
        digits = re.sub(r'\D', '', phone_number)

        if digits.startswith('0'):
            digits = '91' + digits[1:]  # Replace 0 with India country code

        if not digits.startswith('+'):
            digits = '+' + digits

        if self.whatsapp_number.startswith('whatsapp:'):
            digits = f'whatsapp:{digits}'

        return digits

    async def send_sms(self, to_number: str, message: str) -> bool:
        try:
            formatted_number = self._format_phone_number(to_number)
            message = self.client.messages.create(
                body=message,
                from_=self.whatsapp_number,
                to=formatted_number
            )
            return True
        except TwilioRestException as e:
            return False
        except Exception as e:
            return False

    async def send_welcome_message(self, to_number: str) -> None:
        message = (
            "Welcome to the Salon Booking System! 🌟\n\n"
            "Please type exactly one of these options:\n"
            "• Type 'LOGIN' if you're an existing user\n"
            "• Type 'REGISTER' if you're new\n\n"
            "You can type 'cancel' at any time to start over."
        )
        await self.send_sms(to_number, message)

    async def send_registration_prompt(self, to_number: str) -> None:
        message = (
            "Let's get you registered! 📝\n\n"
            "Please provide your details in exactly this format:\n\n"
            "Start by entering your name"
        )
        await self.send_sms(to_number, message)

    async def send_services_list(self, to_number: str, services: List) -> None:
        message = "Available Services:\n\n"
        for i, service in enumerate(services, 1):
            message += f"{i}. {service.name} - ${service.cost}\n"
        message += "\nPlease reply with the number of your chosen service."
        await self.send_sms(to_number, message)

    async def send_salons_list(self, to_number: str, salons: List) -> None:
        message = "Available Salons:\n\n"
        for i, salon in enumerate(salons, 1):
            message += f"{i}. {salon.name} - Rating: {salon.average_rating:.1f}/5.0\n"
        message += "\nPlease reply with the number of your chosen salon."
        await self.send_sms(to_number, message)

    async def send_experts_list(self, to_number: str, experts: List) -> None:
        message = "Available Experts:\n\n"
        for i, expert in enumerate(experts, 1):
            message += f"{i}. {expert.name} - {expert.expertise}\n"
        message += "\nPlease reply with the number of your chosen expert."
        await self.send_sms(to_number, message)

    async def send_date_prompt(self, to_number: str) -> None:
        message = (
            "Please provide your preferred date and time in the following format:\n\n"
            "DATE: YYYY-MM-DD\n"
            "TIME: HH:MM\n\n"
            "Example:\n"
            "DATE: 2024-03-20\n"
            "TIME: 14:30"
        )
        await self.send_sms(to_number, message)

    async def send_appointment_request(self, to_number: str, appointment_details: dict) -> None:
        message = (
            f"New Appointment Request:\n\n"
            f"Appointment ID: {appointment_details['appointment_id']}\n"
            f"Customer: {appointment_details['user_name']}\n"
            f"Service: {appointment_details['service_name']}\n"
            f"Expert: {appointment_details['expert_name']}\n"
            f"Date: {appointment_details['date']}\n"
            f"Time: {appointment_details['time']}\n\n"
            f"To accept, reply: ACCEPT {appointment_details['appointment_id']}\n"
            f"To reject, reply: REJECT {appointment_details['appointment_id']} [reason]"
        )
        await self.send_sms(to_number, message)

    async def send_appointment_confirmation(self, to_number: str, appointment_details: dict) -> None:
        message = (
            f"Your appointment has been confirmed!\n\n"
            f"Service: {appointment_details['service_name']}\n"
            f"Salon: {appointment_details['salon_name']}\n"
            f"Expert: {appointment_details['expert_name']}\n"
            f"Date: {appointment_details['date']}\n"
            f"Time: {appointment_details['time']}\n\n"
            f"We'll send you a reminder 24 hours before your appointment."
        )
        await self.send_sms(to_number, message)

    async def send_appointment_rejection(self, to_number: str, appointment_details: dict, reason: Optional[str] = None) -> None:
        message = (
            f"Your appointment request has been declined.\n\n"
            f"Service: {appointment_details['service_name']}\n"
            f"Date: {appointment_details['date']}\n"
            f"Time: {appointment_details['time']}\n"
        )
        if reason:
            message += f"\nReason: {reason}"
        await self.send_sms(to_number, message)

    async def send_appointment_reminder(self, to_number: str, appointment_details: dict, hours_before: int) -> None:
        message = (
            f"Reminder: You have an appointment in {hours_before} hours!\n\n"
            f"Service: {appointment_details['service_name']}\n"
            f"Salon: {appointment_details['salon_name']}\n"
            f"Expert: {appointment_details['expert_name']}\n"
            f"Date: {appointment_details['date']}\n"
            f"Time: {appointment_details['time']}"
        )
        await self.send_sms(to_number, message)

    async def send_rating_prompt(self, to_number: str) -> None:
        message = (
            "How was your experience? Please rate us from 1 to 5.\n\n"
            "Reply with: RATE X\n"
            "Where X is a number from 1 to 5\n\n"
            "You can also add a comment after your rating."
        )
        await self.send_sms(to_number, message)

    async def send_rating_thank_you(self, to_number: str) -> None:
        message = "Thank you for your feedback! We appreciate your time."
        await self.send_sms(to_number, message)
