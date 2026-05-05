from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.food import FoodRepository

def get_food_repository(
    db: AsyncSession = Depends(get_db),
) -> FoodRepository:
    return FoodRepository(db)
