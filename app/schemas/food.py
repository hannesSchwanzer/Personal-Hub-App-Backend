from enum import Enum
from typing import List, Literal, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from app.schemas.nutrition import NutritionEntity

class FoodType(Enum):
    GENERIC = "generic"
    PRODUCT = "product"

class GenericFoodEntity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    nutrition: NutritionEntity

class FoodProductEntity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    nutrition: NutritionEntity
    barcode: str
    quantity: Optional[str]
    completeness_score: float = 0
    brand: Optional[str]
    categories: List[str]

class FoodAutoFillEntity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    type: FoodType

class FoodItemTemp(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    barcode: str
    nutrition: dict
