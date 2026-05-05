from typing import Optional
from pydantic import BaseModel

class NutritionEntity(BaseModel):
    energy_kcal_100g: Optional[int] = None
    carbohydrates_100g: Optional[float] = None
    proteins_100g: Optional[float] = None
    fat_100g: Optional[float] = None
    fiber_100g: Optional[float] = None

    sugars_100g: Optional[float] = None
    saturated_fat_100g: Optional[float] = None
    sodium_100g: Optional[float] = None
    alcohol_100g: Optional[float] = None

    omega_3_fat_100g: Optional[float] = None
    omega_6_fat_100g: Optional[float] = None
    trans_fat_100g: Optional[float] = None

    vitamin_c_100g: Optional[float] = None
    vitamin_d_100g: Optional[float] = None
    vitamin_b12_100g: Optional[float] = None
    calcium_100g: Optional[float] = None
    iron_100g: Optional[float] = None
    magnesium_100g: Optional[float] = None
    potassium_100g: Optional[float] = None
    zinc_100g: Optional[float] = None
