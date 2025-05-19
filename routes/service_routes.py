from fastapi import APIRouter, HTTPException
from typing import List
from schemas.service import ServiceCreate, Service
from crud import service_crud

router = APIRouter(
    prefix="/services",
    tags=["services"]
)

@router.post("/", response_model=Service)
async def create_service(service: ServiceCreate):
    return await service_crud.create_service(service)

@router.get("/{service_id}", response_model=Service)
async def get_service(service_id: str):
    service = await service_crud.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

@router.get("/price-range/{min_price}/{max_price}", response_model=List[Service])
async def get_services_by_price_range(min_price: float, max_price: float):
    return await service_crud.get_services_by_price_range(min_price, max_price)

@router.put("/{service_id}", response_model=Service)
async def update_service(service_id: str, service_data: dict):
    service = await service_crud.update_service(service_id, service_data)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

@router.get("/", response_model=List[Service])
async def get_all_services():
    return await service_crud.get_all_services() 