from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from schemas.salon import (
    Salon, SalonCreate, TimeSlot,
    ExpertAvailability, SalonUpdate, SalonStatistics
)
from schemas.salon_dashbboard import SalonDashboard
from crud import salon_crud, expert_crud, rating_crud, appointment_crud
from config.database import get_db, Database
from collections import Counter


router = APIRouter(
    prefix="/salons",
    tags=["salons"]
)

@router.post("/", response_model=Salon)
async def create_salon(salon: SalonCreate, db: Database = Depends(get_db)):
    return await salon_crud.create_salon(salon)

@router.get("/{salon_id}", response_model=Salon)
async def get_salon(salon_id: str, db: Database = Depends(get_db)):
    salon = await salon_crud.get_salon(salon_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    return salon

@router.get("/", response_model=List[Salon])
async def get_all_salons(db: Database = Depends(get_db)):
    return await salon_crud.get_all_salons()

@router.get("/dashboard/{salon_id}", response_model=SalonDashboard)
async def get_salon_dashboard(salon_id: str):
    dashboard = await salon_crud.get_salon_dashboard(salon_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Salon dashboard not found")
    return dashboard

@router.post("/{salon_id}/services", response_model=dict)
async def add_service(salon_id: str, service_data: dict):
    service = await salon_crud.add_service(salon_id, service_data)
    if not service:
        raise HTTPException(status_code=404, detail="Salon not found")
    return service

@router.post("/{salon_id}/experts", response_model=dict)
async def add_expert(salon_id: str, expert_data: dict):
    expert = await salon_crud.add_expert(salon_id, expert_data)
    if not expert:
        raise HTTPException(status_code=404, detail="Salon not found")
    return expert

@router.get("/service/{service_id}", response_model=List[Salon])
async def get_salons_by_service(service_id: str, db: Database = Depends(get_db)):
    return await salon_crud.get_salons_by_service(service_id)

@router.get("/expert/{expert_id}", response_model=List[Salon])
async def get_salons_by_expert(expert_id: str, db: Database = Depends(get_db)):
    return await salon_crud.get_salons_by_expert(expert_id)

@router.post("/{salon_id}/services/{service_id}", response_model=Salon)
async def add_service_to_salon(salon_id: str, service_id: str, db: Database = Depends(get_db)):
    salon = await salon_crud.add_service_to_salon(salon_id, service_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon or service not found")
    return salon

@router.delete("/{salon_id}/services/{service_id}", response_model=Salon)
async def remove_service_from_salon(salon_id: str, service_id: str, db: Database = Depends(get_db)):
    salon = await salon_crud.remove_service_from_salon(salon_id, service_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    return salon

@router.post("/{salon_id}/experts/{expert_id}", response_model=Salon)
async def add_expert_to_salon(salon_id: str, expert_id: str, db: Database = Depends(get_db)):
    salon = await salon_crud.add_expert_to_salon(salon_id, expert_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon or expert not found")
    return salon

@router.delete("/{salon_id}/experts/{expert_id}", response_model=Salon)
async def remove_expert_from_salon(salon_id: str, expert_id: str, db: Database = Depends(get_db)):
    salon = await salon_crud.remove_expert_from_salon(salon_id, expert_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    return salon

@router.get("/{salon_id}/services", response_model=List[str])
async def get_salon_services(salon_id: str, db: Database = Depends(get_db)):
    services = await salon_crud.get_salon_services(salon_id)
    if services is None:
        raise HTTPException(status_code=404, detail="Salon not found")
    return services

@router.get("/{salon_id}/experts", response_model=List[str])
async def get_salon_experts(salon_id: str, db: Database = Depends(get_db)):
    experts = await salon_crud.get_salon_experts(salon_id)
    if experts is None:
        raise HTTPException(status_code=404, detail="Salon not found")
    return experts

@router.get("/{salon_id}/available-slots")
async def get_available_slots_endpoint(
    salon_id: str,
    date: str,  # Format: YYYY-MM-DD
    db: Database = Depends(get_db)
):
    """Get available time slots for a salon on a specific date"""
    try:
        # Verify salon exists
        salon = await salon_crud.get_salon(salon_id)
        if not salon:
            raise HTTPException(status_code=404, detail="Salon not found")
        
        # Parse date
        try:
            booking_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Get available slots
        available_slots = await salon_crud.get_available_time_slots(salon_id, booking_date)
        
        # Convert time slots to string format for JSON response
        formatted_slots = [
            {
                "start_time": slot.start_time.strftime("%I:%M %p"),
                "end_time": slot.end_time.strftime("%I:%M %p")
            }
            for slot in available_slots
        ]
        
        return {"available_slots": formatted_slots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{salon_id}/experts/{expert_id}/availability")
async def get_expert_availability_endpoint(
    salon_id: str,
    expert_id: str,
    db: Database = Depends(get_db)
):
    """Get the availability for an expert"""
    try:
        # Verify salon exists
        salon = await salon_crud.get_salon(salon_id)
        if not salon:
            raise HTTPException(status_code=404, detail="Salon not found")
        
        # Get expert's availability
        availability = await salon_crud.get_expert_availability(salon_id, expert_id)
        if not availability:
            raise HTTPException(status_code=404, detail="Expert availability not found")
        
        return availability
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{salon_id}/experts/{expert_id}/availability")
async def update_expert_availability_endpoint(
    salon_id: str,
    expert_id: str,
    weekday: str,
    availability: List[bool],
    db: Database = Depends(get_db)
):
    """Update the availability for an expert for a specific weekday"""
    try:
        # Verify salon exists
        salon = await salon_crud.get_salon(salon_id)
        if not salon:
            raise HTTPException(status_code=404, detail="Salon not found")
        
        # Verify expert exists in salon
        if expert_id not in salon.experts:
            raise HTTPException(status_code=404, detail="Expert not found in salon")
        
        # Verify weekday is valid
        if weekday not in ["0", "1", "2", "3", "4", "5", "6"]:
            raise HTTPException(
                status_code=400, 
                detail="Invalid weekday. Must be 0-6 (Sunday-Saturday)"
            )
        
        # Verify availability array length
        if len(availability) != 13:
            raise HTTPException(
                status_code=400, 
                detail="Availability array must contain exactly 13 values (9am to 9pm)"
            )
        
        # Update expert's availability
        success = await salon_crud.update_expert_availability(salon_id, expert_id, weekday, availability)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update expert availability")
        
        return {"message": "Expert availability updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{salon_id}", response_model=Salon)
async def update_salon(salon_id: str, salon_update: SalonUpdate, db: Database = Depends(get_db)):
    """
    Update salon information.
    Only the fields provided in the request will be updated.
    """
    # Convert Pydantic model to dict and remove None values
    update_data = salon_update.dict(exclude_unset=True)
    
    # Add updated_at timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    salon = await salon_crud.update_salon(salon_id, update_data)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    return salon

@router.put("/{salon_id}/ratings", response_model=Salon)
async def update_salon_ratings(
    salon_id: str,
    rating_data: dict,
    db: Database = Depends(get_db)
):
    """
    Update salon ratings and total ratings.
    Expected payload:
    {
        "rating": float,  # New rating to add
        "user_id": str,   # ID of the user giving the rating
        "comment": str    # Optional comment
    }
    """
    try:
        # Verify salon exists
        salon = await salon_crud.get_salon(salon_id)
        if not salon:
            raise HTTPException(status_code=404, detail="Salon not found")

        # Validate rating
        rating = rating_data.get("rating")
        if not isinstance(rating, (int, float)) or rating < 1 or rating > 5:
            raise HTTPException(
                status_code=400,
                detail="Rating must be a number between 1 and 5"
            )

        # Add or update rating
        rating_obj = await rating_crud.add_rating(
            salon_id=salon_id,
            user_id=rating_data["user_id"],
            rating=rating,
            comment=rating_data.get("comment")
        )

        if not rating_obj:
            raise HTTPException(
                status_code=400,
                detail="Failed to update rating"
            )

        # Get updated salon data
        updated_salon = await salon_crud.get_salon(salon_id)
        return updated_salon

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{salon_id}/statistics", response_model=SalonStatistics)
async def get_salon_statistics(
    salon_id: str,
    start_date: datetime = Query(..., description="Start date for statistics (required)"),
    end_date: Optional[datetime] = Query(None, description="End date for statistics (optional)"),
    db: Database = Depends(get_db)
):
    """
    Get salon statistics including revenue, services used, and experts used within a date range.
    If only start_date is provided, statistics will be for that single day.
    """
    try:
        statistics = await salon_crud.get_salon_statistics(salon_id, start_date, end_date)
        return SalonStatistics(**statistics)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 