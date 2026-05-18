from typing import Iterator, List

from app.repositories.food import FoodRepository
from app.search.repositories.food_search_repository import FoodSearchRepository
from app.schemas.food import FoodProductEntity
from app.search.mappers.food_search_mapper import product_to_search_document


class FoodIndexer:
    """
    Responsible for syncing Postgres Food data → Meilisearch index.
    """

    def __init__(
        self,
        food_repo: FoodRepository,
        food_search_repo: FoodSearchRepository,
        batch_size: int = 500,
    ):
        self.batch_size = batch_size

        self.food_repo = food_repo
        self.search_repo = food_search_repo

    # -------------------------
    # PUBLIC API
    # -------------------------

    async def reindex_all(self):
        """
        Full rebuild of the Meilisearch index.
        Safe to run multiple times.
        """

        print("Starting full food reindex...")

        total = 0

        for batch in self._iterate_food_batches():
            docs = [product_to_search_document(food) for food in batch]

            task_id = self.search_repo.add_or_update_many(docs)

            print(f"Indexed batch of {len(docs)} (task {task_id})")

            total += len(docs)

        print(f"Reindex complete. Total indexed: {total}")

    def index_single_food(self, food_id: int):
        """
        Sync a single food item (for create/update events).
        """

        food = self.food_repo.get_by_id(food_id)

        if not food:
            print(f"Food {food_id} not found, skipping index.")
            return

        doc = to_search_document(food)

        task_id = self.search_repo.add_or_update(doc)

        print(f"Indexed food {food_id} (task {task_id})")

    # -------------------------
    # INTERNAL BATCHING
    # -------------------------

    def _iterate_food_batches(self) -> Iterator[List[FoodProductEntity]]:
        """
        Streams foods from Postgres in batches to avoid memory issues.
        """
        offset = 0

        while True:
            batch = (
                self.food_repo.get_batch(
                    limit=self.batch_size,
                    offset=offset,
                )
            )

            if not batch:
                break

            yield batch
            offset += self.batch_size
