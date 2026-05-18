from fastapi import Depends
from meilisearch import Client

from app.search.repositories.food_search_repository import FoodSearchRepository
from app.search.client import get_search_client


def get_food_search_repository(client: Client = Depends(get_search_client)):
    return FoodSearchRepository(client)
