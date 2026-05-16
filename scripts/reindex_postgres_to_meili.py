import asyncio
from app.search.sync.food_indexer import FoodIndexer

if __name__ == "__main__":


    async def main():
        indexer = FoodIndexer()
        await indexer.reindex_all()

    asyncio.run(main())
