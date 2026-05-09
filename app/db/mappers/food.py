from app.db.models.food import FoodProductDB, GenericFoodDB
from app.schemas.food import GenericFoodEntity, FoodProductEntity
from app.schemas.nutrition import NutritionEntity


def generic_food_to_entity(db_obj: GenericFoodDB) -> GenericFoodEntity:
    return GenericFoodEntity(
        id=db_obj.id,
        name=db_obj.name,
        nutrition=NutritionEntity(**db_obj.nutrition),
    )

def generic_food_to_db(entity: GenericFoodEntity) -> GenericFoodDB:
    return GenericFoodDB(
        id=entity.id,
        name=entity.name,
        nutrition=entity.nutrition.model_dump(),
    )

def food_product_to_entity(db_obj: FoodProductDB) -> FoodProductEntity:
    return FoodProductEntity(
        id=db_obj.id,
        name=db_obj.name,
        nutrition=NutritionEntity(**db_obj.nutrition),
        barcode=db_obj.barcode,
        quantity=db_obj.quantity,
        brand=db_obj.brand,
    )

def food_product_to_db(entity: FoodProductEntity) -> FoodProductDB:
    return FoodProductDB(
        id=entity.id,
        name=entity.name,
        nutrition=entity.nutrition.model_dump(),
        barcode=entity.barcode,
    )
