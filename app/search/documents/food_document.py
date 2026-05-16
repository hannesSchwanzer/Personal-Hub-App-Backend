from pydantic import BaseModel


class FoodDocument(BaseModel):
    id: str

    name: str
    brand: str | None = None

    categories: list[str] = []

    type: str

    completeness_score: float

    name_length: int

    generic_boost: int
