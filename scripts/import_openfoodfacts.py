import gzip
import json
import os
import re
from typing import Optional
from uuid import uuid4
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
from app.schemas import NutritionEntity
from app.schemas.unittype import UnitType

OFF_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"

def get_nutrition_filled_score(nutrition: dict | None) -> float:
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

def get_nutrition(p: dict) -> dict | None:
    def from_nutrition(nutrition: Optional[dict]) -> Optional[NutritionEntity]:
        if not nutrition:
            return None

        nutrients: dict = {}
        unit_set = None
        per_quantity = None

        if "aggregated_set" in nutrition and "nutrients" in nutrition["aggregated_set"]:
            nutrients = nutrition["aggregated_set"]["nutrients"]
            unit_set = nutrition["aggregated_set"].get("per")
        elif "input_sets" in nutrition and nutrition["input_sets"]:
            nutrients = nutrition["input_sets"][0]["nutrients"]
            unit_set = nutrition["input_sets"][0].get("per")
            per_quantity = nutrition["input_sets"][0].get("per_quantity")
        else:
            return None

        NUT_KEYS = {
            "energy_kcal": ["energy-kcal"],
            "carbohydrates": ["carbohydrates"],
            "proteins": ["proteins"],
            "fat": ["fat"],
            "sugars": ["sugars", "added-sugars"],
            "saturated_fat": ["saturated-fat"],
            "sodium": ["sodium"],
        }
        nutrition_args = {}
        for model_key, keys in NUT_KEYS.items():
            value = None
            for k in keys:
                n = nutrients.get(k)
                if n and "value" in n:
                    value = n["value"]
                    break
            nutrition_args[model_key] = value
        if unit_set:
            nutrition_args["quantity_unit"] = UnitType.from_string(unit_set)
            
            unit_number_filtered = ''.join(filter(lambda c: c.isdigit() or c == '.', str(unit_set)))
            if unit_number_filtered:
                nutrition_args["per_quantity"] = float(unit_number_filtered)

        if not nutrition_args.get("quantity_unit") and per_quantity is not None:
            nutrition_args["per_quantity"] = per_quantity
        if any(v is not None for v in nutrition_args.values()):
            return NutritionEntity(**nutrition_args)
        return None

    def from_nutriments(nutriments: Optional[dict]) -> Optional[NutritionEntity]:
        if not nutriments:
            return None
        NUT_KEYS = {
            "energy_kcal": ["energy-kcal_100g", "energy-kcal", "energy_100g", "energy"],
            "carbohydrates": ["carbohydrates_100g", "carbohydrates"],
            "proteins": ["proteins_100g", "proteins"],
            "fat": ["fat_100g", "fat"],
            "sugars": ["sugars_100g", "sugars"],
            "saturated_fat": ["saturated-fat_100g", "saturated-fat"],
            "sodium": ["sodium_100g", "sodium"],
        }
        nutrition_args = {}
        for model_key, off_keys in NUT_KEYS.items():
            value = None
            for off_key in off_keys:
                if off_key in nutriments:
                    value = nutriments[off_key]
                    break
            nutrition_args[model_key] = value

        # assume it is always 100g
        nutrition_args["quantity_unit"] = UnitType.grams
        nutrition_args["per_quantity"] = 100.0

        if any(v is not None for v in nutrition_args.values()):
            return NutritionEntity(**nutrition_args)
        return None

    nutrition = from_nutrition(p.get("nutrition"))

    if not nutrition:
        nutrition = from_nutriments(p.get("nutriments"))

    if not nutrition:
        nutrition = from_nutriments(p.get("nutriments_estimated"))

    return nutrition.model_dump() if nutrition else {}

def map_product(p: dict) -> FoodProductDB | None:
    name = p.get("product_name") # Maybe "generic_name"
    code = p.get("code")
    quantity = p.get("quantity")
    brand = p.get("brands")

    if not name or not code:
        return None

    nutrition = get_nutrition(p)

    completeness_score = get_nutrition_filled_score(nutrition)

    return FoodProductDB(
        id=uuid4(),
        name=name,
        barcode=code,
        nutrition=nutrition,
        quantity=quantity,
        completeness=completeness_score,
        brand=brand,
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
        new_score = product.completeness

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
        FoodProductDB.completeness,
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
                        if product.completeness > existing.nutritionFilledScore:
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

def product_to_dict(p: FoodProductDB) -> dict:
    return {
        "id": str(p.id),
        "name": p.name,
        "barcode": p.barcode,
        "nutrition": p.nutrition,
        "quantity": p.quantity,
        "completeness": p.completeness,
        "brand": p.brand,
    }

async def main():
    url = OFF_URL
    openfoodfacts_file = os.environ.get("OPENFOODFACTS_FILE")
    if openfoodfacts_file:
        file_path = Path(openfoodfacts_file)
        assert file_path.exists(), f"File {file_path} does not exist"
    else:
        file_path = Path("off_products.jsonl.gz")
        print("Downloading dataset...")
        download_file(url, file_path)

    print("Importing into database...")
    await import_file(str(file_path))

    # print("Cleaning up...")
    # file_path.unlink()  # deletes file

    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
