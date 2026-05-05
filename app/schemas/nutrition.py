from typing import Optional
from pydantic import BaseModel

class NutritionEntity(BaseModel):
    calories: Optional[int] = None
    carbohydratesGrams: Optional[float] = None
    sugarGrams: Optional[float] = None
    proteinGrams: Optional[float] = None
    fatGrams: Optional[float] = None
    saturatedFatGrams: Optional[float] = None
    sodiumMilligrams: Optional[float] = None
    fiberGrams: Optional[float] = None

