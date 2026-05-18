from fastapi import Depends
from app.dependencies.repositories import get_food_repository
from app.dependencies.search_repositories import get_food_search_repository
from app.repositories.food import FoodRepository
from app.search.repositories.food_search_repository import FoodSearchRepository
from app.services.food_service import FoodService


async def get_food_service(
    food_repo: FoodRepository = Depends(get_food_repository),
    search_repo: FoodSearchRepository = Depends(get_food_search_repository),
):
    return FoodService(food_repo=food_repo, food_search_repo=search_repo)

