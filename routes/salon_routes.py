from fastapi import APIRouter, HTTPException, Depends
from typing import List
from schemas.salon import Salon, SalonCreate
from schemas.user import SalonDashboard
from crud import salon_crud
from config.database import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(
    prefix="/salons",
    tags=["salons"]
)

@router.post("/", response_model=Salon)
async def create_salon(salon: SalonCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await salon_crud.create_salon(salon)

@router.get("/{salon_id}", response_model=Salon)
async def get_salon(salon_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    salon = await salon_crud.get_salon(salon_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    return salon

@router.get("/owner/{shop_owner_id}", response_model=List[Salon])
async def get_salons_by_owner(shop_owner_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await salon_crud.get_salons_by_owner(shop_owner_id)

@router.put("/{salon_id}", response_model=Salon)
async def update_salon(salon_id: str, salon_data: dict):
    salon = await salon_crud.update_salon(salon_id, salon_data)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    return salon

@router.get("/", response_model=List[Salon])
async def get_all_salons(db: AsyncIOMotorDatabase = Depends(get_db)):
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
async def get_salons_by_service(service_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await salon_crud.get_salons_by_service(service_id)

@router.get("/expert/{expert_id}", response_model=List[Salon])
async def get_salons_by_expert(expert_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await salon_crud.get_salons_by_expert(expert_id)

@router.post("/{salon_id}/services/{service_id}", response_model=Salon)
async def add_service_to_salon(salon_id: str, service_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    salon = await salon_crud.add_service_to_salon(salon_id, service_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon or service not found")
    return salon

@router.delete("/{salon_id}/services/{service_id}", response_model=Salon)
async def remove_service_from_salon(salon_id: str, service_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    salon = await salon_crud.remove_service_from_salon(salon_id, service_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    return salon

@router.post("/{salon_id}/experts/{expert_id}", response_model=Salon)
async def add_expert_to_salon(salon_id: str, expert_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    salon = await salon_crud.add_expert_to_salon(salon_id, expert_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon or expert not found")
    return salon

@router.delete("/{salon_id}/experts/{expert_id}", response_model=Salon)
async def remove_expert_from_salon(salon_id: str, expert_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    salon = await salon_crud.remove_expert_from_salon(salon_id, expert_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    return salon

@router.get("/{salon_id}/services", response_model=List[str])
async def get_salon_services(salon_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    services = await salon_crud.get_salon_services(salon_id)
    if services is None:
        raise HTTPException(status_code=404, detail="Salon not found")
    return services

@router.get("/{salon_id}/experts", response_model=List[str])
async def get_salon_experts(salon_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    experts = await salon_crud.get_salon_experts(salon_id)
    if experts is None:
        raise HTTPException(status_code=404, detail="Salon not found")
    return experts 