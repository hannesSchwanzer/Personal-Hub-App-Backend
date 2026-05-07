from typing import Literal, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from app.schemas.nutrition import NutritionEntity



class GenericFoodEntity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    nutrition: NutritionEntity

class FoodProductEntity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    nutrition: NutritionEntity
    barcode: str

class FoodAutoFillEntity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    type: Literal["generic", "product"]
    nutrition: Optional[NutritionEntity] = None

class FoodItemTemp(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    barcode: str
    nutriton: dict
