from typing import Optional
from pydantic import BaseModel

from app.schemas.unittype import UnitType

class NutritionEntity(BaseModel):
    quantity_unit: Optional[UnitType] = None
    per_quantity: Optional[float] = None

    energy_kcal: Optional[float] = None
    carbohydrates: Optional[float] = None
    proteins: Optional[float] = None
    fat: Optional[float] = None
    sugars: Optional[float] = None
    saturated_fat: Optional[float] = None
    sodium: Optional[float] = None

    # fiber_100g: Optional[float] = None
    # alcohol_100g: Optional[float] = None

    # omega_3_fat_100g: Optional[float] = None
    # omega_6_fat_100g: Optional[float] = None
    # trans_fat_100g: Optional[float] = None
    #
    # vitamin_c_100g: Optional[float] = None
    # vitamin_d_100g: Optional[float] = None
    # vitamin_b12_100g: Optional[float] = None
    # calcium_100g: Optional[float] = None
    # iron_100g: Optional[float] = None
    # magnesium_100g: Optional[float] = None
    # potassium_100g: Optional[float] = None
    # zinc_100g: Optional[float] = None

    @staticmethod
    def from_dict_save(data: dict):
        if data is None:
            return NutritionEntity()
        return NutritionEntity.model_validate(data)
