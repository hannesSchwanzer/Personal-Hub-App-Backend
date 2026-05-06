import gzip
import json
from uuid import uuid4
import os
import requests
from pathlib import Path
import asyncio
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from tqdm import tqdm

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FoodProductDB
from app.db.session import AsyncSessionLocal

OFF_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"

def get_nutrition_filled_score(nutrition: dict) -> float:
    WEIGHTS = {
        "energy_kcal_100g": 3.0,
        "carbohydrates_100g": 2.0,
        "proteins_100g": 2.0,
        "fat_100g": 2.0,
    }

    DEFAULT_WEIGHT = 1.0

    score = 0.0
    max_score = 0.0

    for key, value in nutrition.items():
        weight = WEIGHTS.get(key, DEFAULT_WEIGHT)
        max_score += weight

        if value is not None:
            score += weight

    if max_score == 0:
        return 0.0

    return score / max_score  # normalized 0–1

def merge_nutrition(existing: dict, new: dict) -> tuple[dict, bool]:
    """
    Returns (merged_nutrition, has_conflict)
    """
    merged = {}
    has_conflict = False

    keys = set(existing.keys()) | set(new.keys())

    for key in keys:
        v1 = existing.get(key)
        v2 = new.get(key)

        if v1 is None:
            merged[key] = v2
        elif v2 is None:
            merged[key] = v1
        else:
            if abs(v1 - v2) < 1e-6:
                merged[key] = v1
            else:
                has_conflict = True
                merged[key] = v1  # temp, will be replaced if needed

    return merged, has_conflict


def map_product(p: dict) -> FoodProductDB | None:
    name = p.get("product_name") # Maybe "generic_name"
    code = p.get("code")
    quantity = p.get("quantity")

    if not name or not code:
        return None

    nutriments = p.get("nutriments", {})

    # Map OpenFoodFacts nutriments fields to our NutritionEntity fields
    NUTRITION_KEYS = {
        "energy_kcal_100g": "energy-kcal_100g",
        "carbohydrates_100g": "carbohydrates_100g",
        "proteins_100g": "proteins_100g",
        "fat_100g": "fat_100g",
        "fiber_100g": "fiber_100g",
        "sugars_100g": "sugars_100g",
        "saturated_fat_100g": "saturated-fat_100g",
        "sodium_100g": "sodium_100g",
        "alcohol_100g": "alcohol_100g",
        "omega_3_fat_100g": "omega-3-fat_100g",
        "omega_6_fat_100g": "omega-6-fat_100g",
        "trans_fat_100g": "trans-fat_100g",
        "vitamin_c_100g": "vitamin-c_100g",
        "vitamin_d_100g": "vitamin-d_100g",
        "vitamin_b12_100g": "vitamin-b12_100g",
        "calcium_100g": "calcium_100g",
        "iron_100g": "iron_100g",
        "magnesium_100g": "magnesium_100g",
        "potassium_100g": "potassium_100g",
        "zinc_100g": "zinc_100g",
    }
    nutrition = {}
    for internal_key, off_key in NUTRITION_KEYS.items():
        value = nutriments.get(off_key)
        if value is not None:
            # Convert types; use int for energy, else float for others
            try:
                if internal_key == "energy_kcal_100g":
                    nutrition[internal_key] = int(float(value))
                else:
                    nutrition[internal_key] = float(value)
            except (ValueError, TypeError):
                nutrition[internal_key] = None
        else:
            nutrition[internal_key] = None

    nutritionFilledScore = get_nutrition_filled_score(nutrition)

    return FoodProductDB(
        id=uuid4(),
        name=name,
        barcode=code,
        nutrition=nutrition,
        quantity=quantity,
        nutritionFilledScore=nutritionFilledScore,
    )

async def process_batch(session: AsyncSession, batch: list[FoodProductDB]):
    barcodes = [p.barcode for p in batch]

    db_products = await fetch_existing_products(session, barcodes)

    final_batch = []
    for product in batch:
        db = db_products.get(product.barcode)

        if not db:
            final_batch.append(product)
            continue

        db_nutrition = db["nutrition"]
        db_score = db["score"]
        new_score = product.nutritionFilledScore

        merged, conflict = merge_nutrition(db_nutrition, product.nutrition)

        if not conflict:
            product.nutrition = merged
            final_batch.append(product)
            continue

        if new_score > db_score:
            product.nutrition = merged
            final_batch.append(product)
            continue

    if not final_batch:
        return

    values = [
        {
            "id": p.id,
            "name": p.name,
            "barcode": p.barcode,
            "nutrition": p.nutrition,
            "quantity": p.quantity,
            "nutritionFilledScore": p.nutritionFilledScore,
        }
        for p in final_batch
    ]

    stmt = insert(FoodProductDB).values(values)

    stmt = stmt.on_conflict_do_update(
        index_elements=["barcode"],
        set_={
            "name": stmt.excluded.name,
            "nutrition": stmt.excluded.nutrition,
            "quantity": stmt.excluded.quantity,
            "nutritionFilledScore": stmt.excluded.nutritionFilledScore,
        },
    )

    await session.execute(stmt)
    await session.commit()

async def fetch_existing_products(session: AsyncSession, barcodes: list[str]):
    if not barcodes:
        return {}

    stmt = select(
        FoodProductDB.barcode,
        FoodProductDB.nutrition,
        FoodProductDB.nutritionFilledScore,
    ).where(FoodProductDB.barcode.in_(barcodes))

    result = await session.execute(stmt)

    return {
        barcode: {
            "nutrition": nutrition or {},
            "score": score or 0.0,
        }
        for barcode, nutrition, score in result.all()
    }

async def import_file(path: str, batch_size: int = 500):
    batch = []
    batch_by_barcode = {}

    async with AsyncSessionLocal() as session:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in tqdm(f, desc="Importing products"):
                try:
                    p = json.loads(line)
                except json.JSONDecodeError:
                    continue

                product = map_product(p)
                if not product:
                    continue

                code = product.barcode

                if code in batch_by_barcode:
                    existing = batch_by_barcode[code]

                    merged, conflict = merge_nutrition(
                        existing.nutrition,
                        product.nutrition
                    )

                    if not conflict:
                        existing.nutrition = merged
                    else:
                        if product.nutritionFilledScore > existing.nutritionFilledScore:
                            batch_by_barcode[code] = product

                    continue

                batch.append(product)
                batch_by_barcode[code] = product

                if len(batch) >= batch_size:
                    await process_batch(session, batch)
                    batch = []
                    batch_by_barcode = {}

            if batch:
                await process_batch(session, batch)


def download_file(url: str, target_path: Path):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept": "*/*",
    }

    with requests.get(url, stream=True, headers=headers) as r:
        r.raise_for_status()

        total = int(r.headers.get('content-length', 0))
        with open(target_path, "wb") as f, tqdm(
            total=total, unit='B', unit_scale=True, desc=str(target_path)
        ) as pbar:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))

async def main():
    url = OFF_URL

    file_path = Path("off_products.jsonl.gz")

    print("Downloading dataset...")
    download_file(url, file_path)

    print("Importing into database...")
    await import_file(str(file_path))

    print("Cleaning up...")
    file_path.unlink()  # deletes file

    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
