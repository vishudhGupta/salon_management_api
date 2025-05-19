from fastapi import APIRouter, HTTPException
from typing import List
from schemas.shop_owner import ShopOwnerCreate, ShopOwner
from crud import shop_owner_crud

router = APIRouter(
    prefix="/shop-owners",
    tags=["shop-owners"]
)

@router.post("/", response_model=ShopOwner)
async def create_shop_owner(shop_owner: ShopOwnerCreate):
    return await shop_owner_crud.create_shop_owner(shop_owner)

@router.get("/{shop_owner_id}", response_model=ShopOwner)
async def get_shop_owner(shop_owner_id: str):
    shop_owner = await shop_owner_crud.get_shop_owner(shop_owner_id)
    if not shop_owner:
        raise HTTPException(status_code=404, detail="Shop owner not found")
    return shop_owner

@router.get("/user/{user_id}", response_model=ShopOwner)
async def get_shop_owner_by_user_id(user_id: str):
    shop_owner = await shop_owner_crud.get_shop_owner_by_user_id(user_id)
    if not shop_owner:
        raise HTTPException(status_code=404, detail="Shop owner not found")
    return shop_owner

@router.put("/{shop_owner_id}", response_model=ShopOwner)
async def update_shop_owner(shop_owner_id: str, shop_owner_data: dict):
    shop_owner = await shop_owner_crud.update_shop_owner(shop_owner_id, shop_owner_data)
    if not shop_owner:
        raise HTTPException(status_code=404, detail="Shop owner not found")
    return shop_owner

@router.get("/", response_model=List[ShopOwner])
async def get_all_shop_owners():
    return await shop_owner_crud.get_all_shop_owners() 