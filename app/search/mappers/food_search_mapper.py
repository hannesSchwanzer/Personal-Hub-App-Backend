
from app.schemas.food import FoodProductEntity, FoodType
from app.search.documents.food_document import FoodDocument


def product_to_search_document(food: FoodProductEntity) -> FoodDocument:
    return FoodDocument(
        id=str(food.id),
        name=food.name,
        brand=food.brand if food.brand else None,
        categories=[c for c in food.categories],
        type=FoodType.PRODUCT.value,
        completeness_score=food.completeness_score,
        name_length=len(food.name),
        generic_boost=0
    )
