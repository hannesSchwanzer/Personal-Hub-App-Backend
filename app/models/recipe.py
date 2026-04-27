from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

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

class NutritionInfoEntity(BaseModel):
    calories: Optional[int] = None
    carbohydratesGrams: Optional[float] = None
    sugarGrams: Optional[float] = None
    proteinGrams: Optional[float] = None
    fatGrams: Optional[float] = None
    saturatedFatGrams: Optional[float] = None
    sodiumMilligrams: Optional[float] = None
    fiberGrams: Optional[float] = None

class RecipeEntity(BaseModel):
    name: str
    description: str
    ingredients: List[IngredientEntity]
    steps: List[StepEntity]
    servings: int
    duration: Optional[DurationEntity] = None
    nutritionInfo: Optional[NutritionInfoEntity] = None
    imageUrl: Optional[str] = None

class DurationEntity(BaseModel):
    prepTimeMinutes: Optional[int] = None
    cookTimeMinutes: Optional[int] = None
    restTimeMinutes: Optional[int] = None

