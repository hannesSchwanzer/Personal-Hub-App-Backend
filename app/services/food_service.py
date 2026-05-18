from typing import List, Literal, Optional, Union
from uuid import UUID
from app.repositories.food import FoodRepository
from app.schemas.food import FoodAutoFillEntity, FoodProductEntity, GenericFoodEntity
from app.search.repositories.food_search_repository import FoodSearchRepository
from app.search.mappers.food_search_mapper import product_to_search_document


class FoodService:
    def __init__(
        self,
        food_repo: FoodRepository,
        food_search_repo: FoodSearchRepository,
    ):
        self.food_repo = food_repo
        self.search_repo = food_search_repo

    async def add_product(self, item: FoodProductEntity):
        item = self._prepare_prodcut_for_insert(item)
        await self.food_repo.insert_or_update_product(item)

        document = product_to_search_document(item)
        self.search_repo.add_or_update(document)

    async def add_product_conditional(self, item: FoodProductEntity):
        """
        Adds Foodproduct into db. If already exists, checks which Nutrtion is more filled and decides based on that, if to discard new item or replace old one.
        """
        item = self._prepare_prodcut_for_insert(item)
        
        db_item = await self.food_repo.get_product_by_barcode(item.barcode)

        if db_item:
            if item.completeness_score <= db_item.completeness_score:
                item.id = db_item.id  # keep the same ID to update existing record
            else:
                return  # existing item is better or equal, skip

        await self.food_repo.insert_or_update_product(item)

        document = product_to_search_document(item)
        self.search_repo.add_or_update(document)

    async def add_products(self, items: List[FoodProductEntity]):
        items = [self._prepare_prodcut_for_insert(item) for item in items]
        await self.food_repo.bulk_insert_or_update_products(items)

        documents = [product_to_search_document(item) for item in items]
        self.search_repo.add_or_update_many(documents)

    async def add_products_conditional(self, items: List[FoodProductEntity]):
        """
        Adds Foodproducts into db. If already exists, checks which Nutrtion is more filled and decides based on that, if to discard new item or replace old one. Batched
        """
        items = [self._prepare_prodcut_for_insert(item) for item in items]

        db_items = await self.food_repo.get_products_by_barcode([item.barcode for item in items])
        barcode_to_db_item = {item.barcode: item for item in db_items if item.barcode}

        # Collect items, that should be inserted or updated
        items_to_upsert = []
        for item in items:
            db_item = barcode_to_db_item.get(item.barcode)

            if not db_item:
                items_to_upsert.append(item)

            if item.completeness_score > db_item.completeness_score:
                item.id = db_item.id  # keep the same ID to update existing record
                items_to_upsert.append(item)

        if len(items_to_upsert) == 0:
            return

        await self.food_repo.bulk_insert_or_update_products(items_to_upsert)

        documents = [product_to_search_document(item) for item in items_to_upsert]
        self.search_repo.add_or_update_many(documents)

    async def delete_product(self, id: str):
        await self.food_repo.delete_product(UUID(id))
        self.search_repo.delete(id)

    async def get_product(self, id: str) -> Optional[FoodProductEntity]:
        return await self.food_repo.get_product_by_id(UUID(id))

    async def get_product_by_barcode(self, barcode: str) -> Optional[FoodProductEntity]:
        return await self.food_repo.get_product_by_barcode(barcode)

    async def add_generic(self, item: GenericFoodEntity):
        pass

    async def add_generics(self, items: List[GenericFoodEntity]):
        pass

    async def delete_generic(self, id: str):
        pass

    async def get_generic(self, id: str) -> Optional[GenericFoodEntity]:
        pass

    async def get_by_id_and_type(
        self, id: str, type: Literal["generic", "product"]
    ) -> Optional[Union[FoodProductEntity, GenericFoodEntity]]:
        pass

    async def search_autofill(
        self, query: str, limit: int = 10
    ) -> List[FoodAutoFillEntity]:
        documents = self.search_repo.search(query, limit=limit)
        ids_with_type = [(UUID(d.id), d.type) for d in documents]
        return await self.food_repo.get_autofill_entites_by_ids(ids_with_type)

    @staticmethod
    def _prepare_prodcut_for_insert(item: FoodProductEntity) -> FoodProductEntity:
        item.completeness_score = FoodService._get_nutrition_filled_score(item.nutrition.model_dump())
        item.id = item.id or UUID()  # generate new UUID if not provided
        item.name = FoodService._clean_string(item.name)
        item.barcode = FoodService._clean_string(item.barcode)
        item.brand = FoodService._clean_string(item.brand) if item.brand else None
        for category in item.categories:
            category = FoodService._clean_string(category)
        return item

    @staticmethod
    def _get_nutrition_filled_score(nutrition: dict | None) -> float:
        if not nutrition:
            return 0.0

        score = 0.0
        max_score = 0.0

        for _, value in nutrition.items():
            max_score += 1

            if value is not None:
                score += 1

        if max_score == 0:
            return 0.0

        return score / max_score  # normalized 0–1

    @staticmethod
    def _clean_string(s: str) -> str:
        cleaned = s.strip()
        cleaned = cleaned.encode('utf-8', errors='replace').decode('utf-8', errors='replace')  # remove non-UTF-8 chars
        cleaned = cleaned.replace('\x00', '')  # remove null bytes

        return cleaned
