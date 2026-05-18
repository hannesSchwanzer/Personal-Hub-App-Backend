from uuid import uuid4
from sqlalchemy import Computed
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class GenericFoodDB(Base):
    __tablename__ = "generic_foods"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str]
    nutrition: Mapped[dict] = mapped_column(JSONB)

class FoodProductDB(Base):
    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str]
    nutrition: Mapped[dict] = mapped_column(JSONB)
    barcode: Mapped[str] = mapped_column(index=True, unique=True)
    quantity: Mapped[str] = mapped_column(nullable=True)
    completeness_score: Mapped[float]
    brand: Mapped[str] = mapped_column(nullable=True)
    categories: Mapped[list[str]] = mapped_column(JSONB)
