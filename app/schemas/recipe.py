from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

from app.schemas.nutrition import NutritionEntity

class UnitType(str, Enum):
    miligrams = "miligrams"
    grams = "grams"
    kilograms = "kilograms"
    ounces = "ounces"
    pounds = "pounds"
    milliliters = "milliliters"
    liters = "liters"
    fluidOunces = "fluidOunces"
    gallons = "gallons"
    pieces = "pieces"
    teaspoons = "teaspoons"
    tablespoons = "tablespoons"
    centimeters = "centimeters"
    pinches = "pinches"

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

