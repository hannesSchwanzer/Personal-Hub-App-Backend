import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends

from app.dependencies.repositories import get_food_repository
from app.dependencies.services import get_food_service
from app.repositories.food import FoodRepository
from app.schemas.food import FoodAutoFillEntity, FoodProductEntity
from app.services.food_service import FoodService

router = APIRouter(prefix="/food", tags=["food"])
logger = logging.getLogger(__name__)

@router.get("/search", response_model=List[FoodAutoFillEntity])
async def search_food_item(
    query: str,
    limit: int = 10,
    service: FoodService = Depends(get_food_service),
):
    return await service.search_autofill(query, limit)

@router.get("/getById", response_model=Optional[FoodProductEntity])
async def get_by_id(
    id: UUID,
    repo: FoodRepository = Depends(get_food_repository),
):
    return await repo.get_product_by_id(id)

@router.get("/getByBarcode", response_model=Optional[FoodProductEntity])
async def get_by_barcode(
    barcode: str,
    repo: FoodRepository = Depends(get_food_repository),
):
    return await repo.get_product_by_barcode(barcode)
