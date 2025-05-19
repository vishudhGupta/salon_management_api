from fastapi import APIRouter, HTTPException
from typing import List
from schemas.user import UserCreate, User, UserLogin, UserDashboard
from crud import user_crud

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.post("/login", response_model=User)
async def login_user(login_data: UserLogin):
    user = await user_crud.get_user_by_phone(login_data.phone_number)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/dashboard/{user_id}", response_model=UserDashboard)
async def get_user_dashboard(user_id: str):
    dashboard = await user_crud.get_user_dashboard(user_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="User dashboard not found")
    return dashboard

@router.post("/", response_model=User)
async def create_user(user: UserCreate):
    return await user_crud.create_user(user)

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = await user_crud.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/email/{email}", response_model=User)
async def get_user_by_email(email: str):
    user = await user_crud.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=User)
async def update_user(user_id: str, user_data: dict):
    user = await user_crud.update_user(user_id, user_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/", response_model=List[User])
async def get_all_users():
    return await user_crud.get_all_users() 