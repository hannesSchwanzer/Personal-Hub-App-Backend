from typing import List, Literal, Optional, Union
from uuid import UUID
from app.repositories.food import FoodRepository
from app.schemas.food import FoodAutoFillEntity, FoodProductEntity, GenericFoodEntity
from app.search.repositories.food_search_repository import FoodSearchRepository

class FoodService:
    def __init__(
        self,
        food_repo: FoodRepository,
        food_search_repo: FoodSearchRepository,
    ):
        self.food_repo = food_repo
        self.search_repo = food_search_repo

    async def add_product(self, item: FoodProductEntity):
        pass

    async def add_product_conditional(self, item: FoodProductEntity):
        """
        Adds Foodproduct into db. If already exists, checks which Nutrtion is more filled and decides based on that, if to discard new item or replace old one.
        """
        pass

    async def add_products(self, items: List[FoodProductEntity]):
        pass

    async def add_products_conditional(self, items: List[FoodProductEntity]):
        """
        Adds Foodproducts into db. If already exists, checks which Nutrtion is more filled and decides based on that, if to discard new item or replace old one. Batched
        """
        pass

    async def delete_product(self, id: str):
        pass

    async def get_product(self, id: str) -> Optional[FoodProductEntity]:
        pass

    async def get_product_by_barcode(self, barcode: str) -> Optional[FoodProductEntity]:
        pass

    async def add_generic(self, item: GenericFoodEntity):
        pass

    async def add_generics(self, items: List[GenericFoodEntity]):
        pass

    async def delete_generic(self, id: str):
        pass

    async def get_generic(self, id: str) -> Optional[GenericFoodEntity]:
        pass

    async def get_by_id_and_type(self, id: str, type: Literal["generic", "product"]) -> Optional[Union[FoodProductEntity, GenericFoodEntity]]:
        pass

    async def search_autofill(self, query: str, limit: int = 10) -> List[FoodAutoFillEntity]:
        documents = self.search_repo.search(query, limit=limit)
        ids_with_type = [(UUID(d.id), d.type) for d in documents]
        return await self.food_repo.get_autofill_entites_by_ids(ids_with_type)

