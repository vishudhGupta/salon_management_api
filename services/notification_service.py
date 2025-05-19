from config.database import Database, get_db
from fastapi import Depends
from datetime import datetime

class NotificationService:
    def __init__(self, db: Database = Depends(get_db)):
        self.db = db

    async def send_appointment_status_notification(self, user_id: str, appointment_id: str, status: str):
        """Send notification about appointment status change to user"""
        notification = {
            "user_id": user_id,
            "appointment_id": appointment_id,
            "type": "appointment_status",
            "status": status,
            "message": self._get_status_message(status),
            "created_at": datetime.utcnow(),
            "read": False
        }
        
        # Store notification in database
        await self.db.notifications.insert_one(notification)
        
        # Update user's notifications array
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$addToSet": {"notifications": notification}}
        )

    def _get_status_message(self, status: str) -> str:
        """Get appropriate message based on appointment status"""
        messages = {
            "confirmed": "Your appointment has been confirmed!",
            "cancelled": "Your appointment has been cancelled.",
            "completed": "Your appointment has been completed.",
            "pending": "Your appointment is pending confirmation."
        }
        return messages.get(status, f"Your appointment status has been updated to {status}.") 