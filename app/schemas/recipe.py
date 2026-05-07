from typing import List, Optional
from pydantic import BaseModel

from app.schemas.nutrition import NutritionEntity
from app.schemas.unittype import UnitType


class IngredientEntity(BaseModel):
    name: str
    quantity: float
    unit: UnitType
    additionalInfo: Optional[str] = None


class StepIngredientEntity(BaseModel):
    name: str
    quantityPercent: float

class StepEntity(BaseModel):
    ingredients: List[StepIngredientEntity]
    instruction: str

class DurationEntity(BaseModel):
    prepTimeMinutes: Optional[int] = None
    cookTimeMinutes: Optional[int] = None
    restTimeMinutes: Optional[int] = None

class RecipeEntity(BaseModel):
    name: str
    description: str
    ingredients: List[IngredientEntity]
    steps: List[StepEntity]
    servings: int
    duration: Optional[DurationEntity] = None
    nutritionInfo: Optional[NutritionEntity] = None
    imageUrl: Optional[str] = None

