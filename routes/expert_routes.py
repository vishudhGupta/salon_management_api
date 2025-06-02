from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from datetime import datetime
from schemas.expert import Expert, ExpertCreate, ExpertUpdate, ExpertAvailability
from schemas.salon import TimeSlot
from crud import expert_crud
from config.database import get_db, Database

router = APIRouter(
    prefix="/experts",
    tags=["experts"]
)

@router.post("/", response_model=Expert)
async def create_expert(expert: ExpertCreate, db: Database = Depends(get_db)):
    return await expert_crud.create_expert(expert)

@router.get("/{expert_id}", response_model=Expert)
async def get_expert(expert_id: str, db: Database = Depends(get_db)):
    expert = await expert_crud.get_expert(expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")
    return expert

@router.get("/", response_model=List[Expert])
async def get_all_experts(db: Database = Depends(get_db)):
    return await expert_crud.get_all_experts()

@router.put("/{expert_id}", response_model=Expert)
async def update_expert(expert_id: str, expert: ExpertUpdate, db: Database = Depends(get_db)):
    updated_expert = await expert_crud.update_expert(expert_id, expert)
    if not updated_expert:
        raise HTTPException(status_code=404, detail="Expert not found")
    return updated_expert

@router.delete("/{expert_id}")
async def delete_expert(expert_id: str, db: Database = Depends(get_db)):
    success = await expert_crud.delete_expert(expert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Expert not found")
    return {"message": "Expert deleted successfully"}

@router.get("/{expert_id}/availability", response_model=ExpertAvailability)
async def get_expert_availability_endpoint(
    expert_id: str,
    db: Database = Depends(get_db)
):
    """Get availability for an expert"""
    availability = await expert_crud.get_expert_availability(expert_id)
    if not availability:
        raise HTTPException(status_code=404, detail="Availability not found")
    return availability

@router.get("/{salon_id}/available-experts")
async def get_available_experts_endpoint(
    salon_id: str,
    date: str,  # Format: YYYY-MM-DD
    time_slot: TimeSlot,
    db: Database = Depends(get_db)
):
    """Get available experts for a salon at a specific time slot"""
    try:
        # Parse date
        booking_date = datetime.strptime(date, "%Y-%m-%d")
        
        # Get available experts
        available_experts = await expert_crud.get_available_experts(salon_id, booking_date, time_slot)
        return {"available_experts": available_experts}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD") 