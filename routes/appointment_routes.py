from fastapi import APIRouter, HTTPException
from typing import List
from schemas.appointment import AppointmentCreate, Appointment
from crud import appointment_crud

router = APIRouter(
    prefix="/appointments",
    tags=["appointments"]
)

@router.post("/", response_model=Appointment)
async def create_appointment(appointment: AppointmentCreate):
    return await appointment_crud.create_appointment(appointment)

@router.get("/{appointment_id}", response_model=Appointment)
async def get_appointment(appointment_id: str):
    appointment = await appointment_crud.get_appointment(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment

@router.get("/user/{user_id}", response_model=List[Appointment])
async def get_user_appointments(user_id: str):
    return await appointment_crud.get_user_appointments(user_id)

@router.get("/salon/{salon_id}", response_model=List[Appointment])
async def get_salon_appointments(salon_id: str):
    return await appointment_crud.get_salon_appointments(salon_id)

@router.get("/expert/{expert_id}", response_model=List[Appointment])
async def get_expert_appointments(expert_id: str):
    return await appointment_crud.get_expert_appointments(expert_id)

@router.put("/{appointment_id}", response_model=Appointment)
async def update_appointment(appointment_id: str, appointment_data: dict):
    appointment = await appointment_crud.update_appointment(appointment_id, appointment_data)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment

@router.post("/{appointment_id}/cancel", response_model=Appointment)
async def cancel_appointment(appointment_id: str):
    appointment = await appointment_crud.cancel_appointment(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment

@router.post("/{appointment_id}/confirm", response_model=Appointment)
async def confirm_appointment(appointment_id: str):
    appointment = await appointment_crud.confirm_appointment(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment

@router.get("/user/{user_id}/upcoming", response_model=List[Appointment])
async def get_upcoming_appointments(user_id: str):
    return await appointment_crud.get_upcoming_appointments(user_id)

@router.get("/", response_model=List[Appointment])
async def get_all_appointments():
    return await appointment_crud.get_all_appointments()

@router.post("/{appointment_id}/expert/{expert_id}/confirm", response_model=Appointment)
async def confirm_expert_appointment(appointment_id: str, expert_id: str):
    appointment = await appointment_crud.confirm_expert_appointment(appointment_id, expert_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment 