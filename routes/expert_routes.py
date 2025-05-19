from fastapi import APIRouter, HTTPException
from typing import List
from schemas.expert import ExpertCreate, Expert
from crud import expert_crud

router = APIRouter(
    prefix="/experts",
    tags=["experts"]
)

@router.post("/", response_model=Expert)
async def create_expert(expert: ExpertCreate):
    return await expert_crud.create_expert(expert)

@router.get("/{expert_id}", response_model=Expert)
async def get_expert(expert_id: str):
    expert = await expert_crud.get_expert(expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")
    return expert

@router.get("/expertise/{expertise}", response_model=List[Expert])
async def get_experts_by_expertise(expertise: str):
    return await expert_crud.get_experts_by_expertise(expertise)

@router.put("/{expert_id}", response_model=Expert)
async def update_expert(expert_id: str, expert_data: dict):
    expert = await expert_crud.update_expert(expert_id, expert_data)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")
    return expert

@router.get("/", response_model=List[Expert])
async def get_all_experts():
    return await expert_crud.get_all_experts() 