from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from datetime import datetime
from schemas.salon import (
    Salon, SalonCreate, SalonWorkingHours, TimeSlot,
    ExpertWorkingHours
)
from schemas.salon_dashbboard import SalonDashboard
from crud import salon_crud, expert_crud
from config.database import get_db, Database


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

@router.get("/owner/{shop_owner_id}", response_model=List[Salon])
async def get_salons_by_owner(shop_owner_id: str, db: Database = Depends(get_db)):
    return await salon_crud.get_salons_by_owner(shop_owner_id)

@router.put("/{salon_id}", response_model=Salon)
async def update_salon(salon_id: str, salon_data: dict):
    salon = await salon_crud.update_salon(salon_id, salon_data)
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

@router.get("/{salon_id}/working-hours", response_model=SalonWorkingHours)
async def get_salon_working_hours_endpoint(
    salon_id: str,
    db: Database = Depends(get_db)
):
    """Get working hours for a salon"""
    working_hours = await salon_crud.get_salon_working_hours(salon_id)
    if not working_hours:
        # If no working hours exist, create default (all days available)
        working_hours = SalonWorkingHours(
            salon_id=salon_id,
            is_available=[True, True, True, True, True, True, True]
        )
        await salon_crud.update_salon_working_hours(salon_id, working_hours)
    return working_hours

@router.put("/{salon_id}/working-hours", response_model=SalonWorkingHours)
async def update_salon_working_hours_endpoint(
    salon_id: str,
    working_hours: SalonWorkingHours,
    db: Database = Depends(get_db)
):
    """Update working hours for a salon"""
    # Verify salon exists
    salon = await salon_crud.get_salon(salon_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    
    # Update working hours
    updated_hours = await salon_crud.update_salon_working_hours(salon_id, working_hours)
    return updated_hours

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
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M")
            }
            for slot in available_slots
        ]
        
        return {"available_slots": formatted_slots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{salon_id}/experts/{expert_id}/working-status")
async def update_expert_working_status(
    salon_id: str,
    expert_id: str,
    is_working: bool,
    db: Database = Depends(get_db)
):
    """
    Update the working status of an expert.
    Set isWorking to True when they start a service and False when they finish.
    """
    try:
        # Verify salon exists
        salon = await salon_crud.get_salon(salon_id)
        if not salon:
            raise HTTPException(status_code=404, detail="Salon not found")
        
        # Verify expert exists and belongs to the salon
        expert = await expert_crud.get_expert(expert_id)
        if not expert or expert.salon_id != salon_id:
            raise HTTPException(status_code=404, detail="Expert not found in this salon")
        
        # Update expert's working status
        updated_expert = await expert_crud.set_expert_working_status(expert_id, is_working)
        if not updated_expert:
            raise HTTPException(status_code=400, detail="Failed to update expert working status")
        
        return {"message": "Expert working status updated successfully", "expert": updated_expert}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 