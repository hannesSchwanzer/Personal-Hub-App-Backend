from typing import List, Literal, Optional, Tuple, Union
from uuid import UUID
from sqlalchemy import select, func, case, literal_column, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mappers.food import food_product_to_db, food_product_to_entity
from app.db.models import GenericFoodDB, FoodProductDB
from app.schemas import FoodAutoFillEntity
from app.schemas.food import FoodItemTemp, FoodProductEntity, FoodType, GenericFoodEntity

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

    async def get_products_by_id(self, ids: List[UUID]) -> List[FoodProductEntity]:
        result = await self.db.execute(
            select(FoodProductDB).where(FoodProductDB.id.in_(ids))
        )
        db_products = result.scalars().all()
        return [food_product_to_entity(db_product) for db_product in db_products]

    async def get_product_by_barcode(self, barcode: str) -> Optional[FoodProductEntity]:
        result = await self.db.execute(
            select(FoodProductDB).where(FoodProductDB.barcode == barcode)
        )
        db_product = result.scalar_one_or_none()
        if not db_product:
            return None
        return food_product_to_entity(db_product)

    async def get_products_by_barcode(self, barcodes: List[str]) -> List[FoodProductEntity]:
        result = await self.db.execute(
            select(FoodProductDB).where(FoodProductDB.barcode.in_(barcodes))
        )
        db_products = result.scalars().all()
        return [food_product_to_entity(db_product) for db_product in db_products]

    async def delete_product(self, id: UUID):
        """
        Delete a FoodProductDB with the specified id from the database.
        """
        result = await self.db.execute(
            select(FoodProductDB).where(FoodProductDB.id == id)
        )
        db_product = result.scalar_one_or_none()
        if db_product:
            await self.db.delete(db_product)
            await self.db.commit()

    async def get_generic_by_id(self, id: UUID) -> Optional[GenericFoodEntity]:
        pass

    async def get_generics_by_id(self, ids: List[UUID]) -> List[GenericFoodEntity]:
        return []

    async def insert_or_update_product(self, item: FoodProductEntity) -> FoodProductEntity:
        db_product = food_product_to_db(item)

        merged = await self.db.merge(db_product)
        await self.db.commit()
        await self.db.refresh(merged)
        return food_product_to_entity(merged)

    async def bulk_insert_or_update_products(self, items: List[FoodProductEntity]):
        # True PostgreSQL bulk upsert using SQLAlchemy Core
        db_products = [food_product_to_db(item) for item in items]
        # Convert ORM models to dicts; handle missing attributes if needed
        db_dicts = []
        for db_product in db_products:
            db_dicts.append({
                'id': db_product.id,
                'name': db_product.name,
                'barcode': db_product.barcode,
                'nutrition': db_product.nutrition,
                'quantity': db_product.quantity,
                'completeness': db_product.completeness_score,
                'brand': db_product.brand,
            })

        stmt = insert(FoodProductDB).values(db_dicts)
        # Exclude primary key for sets_ in update, update all others. You may want to adjust fields.
        update_dict = {
            'name': stmt.excluded.name,
            'barcode': stmt.excluded.barcode,
            'nutrition': stmt.excluded.nutrition,
            'quantity': stmt.excluded.quantity,
            'completeness': stmt.excluded.completeness,
            'brand': stmt.excluded.brand,
        }
        # Upsert on primary key (id)
        stmt = stmt.on_conflict_do_update(
            index_elements=['id'],
            set_=update_dict
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def get_autofill_entites_by_ids(self, ids_with_type: List[Tuple[UUID, str]]) -> List[FoodAutoFillEntity]:
        ids_product = [id for id, type in ids_with_type if type == FoodType.PRODUCT.value]
        ids_generic = [id for id, type in ids_with_type if type == FoodType.GENERIC.value]

        products = []
        if ids_product:
            result = await self.db.execute(
                select(FoodProductDB.id, FoodProductDB.name)
                .where(FoodProductDB.id.in_(ids_product))
            )
            products = result.all()

        generics = []
        if ids_generic:
            result = await self.db.execute(
                select(GenericFoodDB.id, GenericFoodDB.name)
                .where(GenericFoodDB.id.in_(ids_generic))
            )
            generics = result.all()

        return [
            FoodAutoFillEntity(
                id=row.id,
                name=row.name,
                type=FoodType.PRODUCT
            )
            for row in products
        ] + [
            FoodAutoFillEntity(
                id=row.id,
                name=row.name,
                type=FoodType.GENERIC
            )
            for row in generics
        ]

