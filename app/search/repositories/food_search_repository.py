from typing import List
from meilisearch import Client

from app.search.documents.food_document import FoodDocument
from indices import FOODS_INDEX


class FoodSearchRepository:
    def __init__(self, client: Client):
        self.client = client
        self.index = self.client.index(FOODS_INDEX)

    def add_or_update(self, doc: FoodDocument):
        """
        Insert or update a single food document.
        """
        task = self.index.add_documents([doc.model_dump()])
        return task.task_uid

    def add_or_update_many(self, docs: list[FoodDocument]):
        """
        Bulk insert/update.
        """
        payload = [d.model_dump() for d in docs]
        task = self.index.add_documents(payload)
        return task.task_uid

    def delete(self, food_id: int):
        """
        Remove document from index.
        """
        task = self.index.delete_document(food_id)
        return task.task_uid

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        filter_: str | None = None,
    ) -> List[FoodDocument]:
        """
        General search (used for autocomplete too).
        """
        params = {
            "limit": limit,
        }

        if filter_:
            params["filter"] = filter_

        result = self.index.search(query, params)
        return [FoodDocument.validate(d) for d in result]

    def autocomplete(self, query: str, limit: int = 8):
        """
        Lightweight autocomplete variant.
        """
        return self.index.search(
            query,
            {
                "limit": limit,
                "attributesToHighlight": ["name"],
            },
        )

    def get_by_id(self, food_id: int):
        """
        Fetch single document from index.
        Useful for debugging or sync checks.
        """
        return self.index.get_document(food_id)

