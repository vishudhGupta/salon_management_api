from typing import List, Optional
from schemas.shop_owner import ShopOwnerCreate, ShopOwner, generate_shop_owner_id
from config.database import Database

async def create_shop_owner(shop_owner: ShopOwnerCreate) -> ShopOwner:
    db = Database.get_db()
    shop_owner_id = generate_shop_owner_id(shop_owner.user_id)
    shop_owner_dict = shop_owner.dict()
    shop_owner_dict["shop_owner_id"] = shop_owner_id
    shop_owner_dict["salons"] = []
    
    await db.shop_owners.insert_one(shop_owner_dict)
    return ShopOwner(**shop_owner_dict)

async def get_shop_owner(shop_owner_id: str) -> Optional[ShopOwner]:
    db = Database.get_db()
    shop_owner = await db.shop_owners.find_one({"shop_owner_id": shop_owner_id})
    return ShopOwner(**shop_owner) if shop_owner else None

async def get_shop_owner_by_user_id(user_id: str) -> Optional[ShopOwner]:
    db = Database.get_db()
    shop_owner = await db.shop_owners.find_one({"user_id": user_id})
    return ShopOwner(**shop_owner) if shop_owner else None

async def update_shop_owner(shop_owner_id: str, shop_owner_data: dict) -> Optional[ShopOwner]:
    db = Database.get_db()
    update_result = await db.shop_owners.update_one(
        {"shop_owner_id": shop_owner_id},
        {"$set": shop_owner_data}
    )
    if update_result.modified_count:
        return await get_shop_owner(shop_owner_id)
    return None

async def get_all_shop_owners() -> List[ShopOwner]:
    db = Database.get_db()
    shop_owners = await db.shop_owners.find().to_list(length=None)
    return [ShopOwner(**shop_owner) for shop_owner in shop_owners] 