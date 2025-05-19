from typing import List, Optional
from schemas.salon import Rating
from config.database import Database
from datetime import datetime

async def add_rating(salon_id: str, user_id: str, rating: float, comment: Optional[str] = None) -> Optional[Rating]:
    db = Database.get_db()
    
    # Create rating object
    rating_obj = Rating(
        user_id=user_id,
        rating=rating,
        comment=comment,
        created_at=datetime.utcnow()
    )
    
    # Add rating to salon's ratings array
    update_result = await db.salons.update_one(
        {"salon_id": salon_id},
        {
            "$push": {"ratings": rating_obj.dict()},
            "$inc": {"total_ratings": 1}
        }
    )
    
    if update_result.modified_count:
        # Recalculate average rating
        salon = await db.salons.find_one({"salon_id": salon_id})
        if salon and "ratings" in salon:
            total_rating = sum(r["rating"] for r in salon["ratings"])
            avg_rating = total_rating / len(salon["ratings"])
            
            # Update average rating
            await db.salons.update_one(
                {"salon_id": salon_id},
                {"$set": {"average_rating": avg_rating}}
            )
        
        return rating_obj
    return None

async def get_salon_ratings(salon_id: str) -> List[Rating]:
    db = Database.get_db()
    salon = await db.salons.find_one({"salon_id": salon_id})
    if salon and "ratings" in salon:
        return [Rating(**rating) for rating in salon["ratings"]]
    return []

async def get_user_ratings(user_id: str) -> List[Rating]:
    db = Database.get_db()
    # Find all salons where the user has left a rating
    salons = await db.salons.find(
        {"ratings.user_id": user_id}
    ).to_list(length=None)
    
    # Extract all ratings by this user
    user_ratings = []
    for salon in salons:
        if "ratings" in salon:
            for rating in salon["ratings"]:
                if rating["user_id"] == user_id:
                    user_ratings.append(Rating(**rating))
    
    return user_ratings

async def update_rating(salon_id: str, user_id: str, new_rating: float, new_comment: Optional[str] = None) -> Optional[Rating]:
    db = Database.get_db()
    
    # Update the rating in salon's ratings array
    update_result = await db.salons.update_one(
        {
            "salon_id": salon_id,
            "ratings.user_id": user_id
        },
        {
            "$set": {
                "ratings.$.rating": new_rating,
                "ratings.$.comment": new_comment,
                "ratings.$.created_at": datetime.utcnow()
            }
        }
    )
    
    if update_result.modified_count:
        # Recalculate average rating
        salon = await db.salons.find_one({"salon_id": salon_id})
        if salon and "ratings" in salon:
            total_rating = sum(r["rating"] for r in salon["ratings"])
            avg_rating = total_rating / len(salon["ratings"])
            
            # Update average rating
            await db.salons.update_one(
                {"salon_id": salon_id},
                {"$set": {"average_rating": avg_rating}}
            )
        
        return Rating(
            user_id=user_id,
            rating=new_rating,
            comment=new_comment,
            created_at=datetime.utcnow()
        )
    return None

async def delete_rating(salon_id: str, user_id: str) -> bool:
    db = Database.get_db()
    
    # Remove the rating from salon's ratings array
    update_result = await db.salons.update_one(
        {"salon_id": salon_id},
        {
            "$pull": {"ratings": {"user_id": user_id}},
            "$inc": {"total_ratings": -1}
        }
    )
    
    if update_result.modified_count:
        # Recalculate average rating
        salon = await db.salons.find_one({"salon_id": salon_id})
        if salon and "ratings" in salon:
            if salon["ratings"]:  # If there are still ratings
                total_rating = sum(r["rating"] for r in salon["ratings"])
                avg_rating = total_rating / len(salon["ratings"])
            else:
                avg_rating = 0.0
            
            # Update average rating
            await db.salons.update_one(
                {"salon_id": salon_id},
                {"$set": {"average_rating": avg_rating}}
            )
        
        return True
    return False 