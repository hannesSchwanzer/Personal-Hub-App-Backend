from typing import List, Optional
from pydantic import BaseModel

from app.schemas.nutrition import NutritionEntity
from app.schemas.unittype import UnitType


class IngredientEntity(BaseModel):
    name: str
    quantity: float = 1
    unit: UnitType = UnitType.pieces
    additionalInfo: Optional[str] = None

    @staticmethod
    def from_dict_save(data: dict):
        if data is None:
            return IngredientEntity(name="", quantity=1, unit=UnitType.pieces, additionalInfo=None)
        name = data.get("name", "")
        quantity = data.get("quantity", 1)
        unit_str = data.get("unit", "pieces")
        additional_info = data.get("additionalInfo")

        return IngredientEntity(
            name=name if name is not None else "",
            quantity=quantity if quantity is not None else 1,
            unit=UnitType.from_string(unit_str) if unit_str is not None else UnitType.pieces,
            additionalInfo=additional_info
        )


class StepIngredientEntity(BaseModel):
    name: str
    quantityPercent: float = 1.0

    @staticmethod
    def from_dict_save(data: dict):
        if data is None:
            return StepIngredientEntity(name="", quantityPercent=1.0)
        name = data.get("name", "")
        quantity_percent = data.get("quantityPercent", 1.0)

        return StepIngredientEntity(
            name=name if name is not None else "",
            quantityPercent=quantity_percent if quantity_percent is not None else 1.0
        )

class StepEntity(BaseModel):
    ingredients: List[StepIngredientEntity] = []
    instruction: str

    @staticmethod
    def from_dict_save(data: dict):
        if data is None:
            return StepEntity(ingredients=[], instruction="")
        instruction = data.get("instruction", "")
        ingredients_data = data.get("ingredients", [])
        return StepEntity(
            instruction=instruction if instruction is not None else "",
            ingredients=[StepIngredientEntity.from_dict_save(ing) for ing in ingredients_data] if ingredients_data is not None else []
        )

class DurationEntity(BaseModel):
    prepTimeMinutes: Optional[int] = None
    cookTimeMinutes: Optional[int] = None
    restTimeMinutes: Optional[int] = None

    @staticmethod
    def from_dict_save(data: dict):
        if data is None:
            return DurationEntity()
        return DurationEntity.model_validate(data)


class RecipeEntity(BaseModel):
    name: str
    description: str = ""
    ingredients: List[IngredientEntity]
    steps: List[StepEntity]
    servings: int = 1
    duration: DurationEntity = DurationEntity()
    nutritionInfo: NutritionEntity = NutritionEntity()
    imageUrl: Optional[str] = None

    @staticmethod
    def from_dict_safe(data: dict):
        if data == None:
            return RecipeEntity(
                name="",
                description="",
                ingredients=[],
                steps=[],
                servings=1,
                duration=DurationEntity(),
                nutritionInfo=NutritionEntity(),
                imageUrl=None
            )
        name = data.get("name", "")
        description = data.get("description", "")
        ingredients_data = data.get("ingredients", [])
        steps_data = data.get("steps", [])
        servings = data.get("servings", 1)
        duration_data = data.get("duration", {})
        nutrition_info_data = data.get("nutritionInfo", {})
        image_url = data.get("imageUrl")

        return RecipeEntity(
            name=name if name is not None else "",
            description=description if description is not None else "",
            ingredients=[IngredientEntity.from_dict_save(ing) for ing in ingredients_data] if ingredients_data is not None else [],
            steps=[StepEntity.from_dict_save(step) for step in steps_data] if steps_data is not None else [],
            servings=servings if servings is not None else 1,
            duration=DurationEntity.from_dict_save(duration_data),
            nutritionInfo=NutritionEntity.from_dict_save(nutrition_info_data),
            imageUrl=image_url
        )



