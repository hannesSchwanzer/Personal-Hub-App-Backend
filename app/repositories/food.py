from typing import List, Literal, Optional, Union
from uuid import UUID
from sqlalchemy import select, func, case, literal_column, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mappers.food import food_product_to_entity
from app.db.models import GenericFoodDB, FoodProductDB
from app.schemas import FoodAutoFillEntity
from app.schemas.food import FoodItemTemp, FoodProductEntity, GenericFoodEntity

class FoodRepository():
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id_and_type(self, id: UUID, type: Literal["generic", "product"]) -> Optional[Union[FoodProductEntity, GenericFoodEntity]]:
        pass

    async def get_product_by_id(self, id: UUID) -> Optional[FoodProductEntity]:
        result = await self.db.execute(
            select(FoodProductDB).where(FoodProductDB.id == id)
        )
        db_product = result.scalar_one_or_none()
        if not db_product:
            return None
        return food_product_to_entity(db_product)

    async def get_product_by_barcode(self, barcode: str) -> Optional[FoodProductEntity]:
        result = await self.db.execute(
            select(FoodProductDB).where(FoodProductDB.barcode == barcode)
        )
        db_product = result.scalar_one_or_none()
        if not db_product:
            return None
        return food_product_to_entity(db_product)

    async def get_generic_by_id(self, id: UUID) -> Optional[GenericFoodEntity]:
        pass

    async def search_autofill(self, query: str, limit: int = 10) -> List[FoodAutoFillEntity]:
        ts_query = func.websearch_to_tsquery("simple", query)

        generic_rank = (
            func.ts_rank(GenericFoodDB.search_vector, ts_query)
            + 0.2  # small boost for generic foods
            - (func.length(GenericFoodDB.name) / 100.0)
        )

        generic_stmt = (
            select(
                GenericFoodDB.id.label("id"),
                GenericFoodDB.name.label("name"),
                literal_column("'generic'").label("type"),
                generic_rank.label("score"),
            )
            .where(GenericFoodDB.search_vector.op("@@")(ts_query))
        )

        product_rank = (
            func.ts_rank(FoodProductDB.search_vector, ts_query)
            - (func.length(FoodProductDB.name) / 100.0)
            + FoodProductDB.completeness
        )

        product_stmt = (
            select(
                FoodProductDB.id.label("id"),
                FoodProductDB.name.label("name"),
                literal_column("'product'").label("type"),
                product_rank.label("score"),
            )
            .where(FoodProductDB.search_vector.op("@@")(ts_query))
        )

        union = generic_stmt.union_all(product_stmt).subquery()

        # Window function to rank rows by lower(name), type, score desc
        stmt = (
            select(
                union.c.id,
                union.c.name,
                union.c.type,
                union.c.score,
                func.row_number().over(
                    partition_by=[func.lower(union.c.name), union.c.type],
                    order_by=union.c.score.desc()
                ).label("rnum")
            )
        )
        ranked = stmt.subquery()

        final_stmt = (
            select(ranked.c.id, ranked.c.name, ranked.c.type)
            .where(ranked.c.rnum == 1)
            .order_by(ranked.c.score.desc())
            .limit(limit)
        )

        result = await self.db.execute(final_stmt)
        rows = result.all()

        return [
            FoodAutoFillEntity(
                id=row.id,
                name=row.name,
                type=row.type,
            )
            for row in rows
        ]

