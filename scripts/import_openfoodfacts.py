import gzip
import json
from typing import Optional
import requests
from pathlib import Path
import asyncio
from pathlib import Path
from tqdm import tqdm

from app.core.config import settings
from app.db.models import FoodProductDB
from app.db.session import AsyncSessionLocal, get_db
from app.repositories.food import FoodRepository
from app.schemas import NutritionEntity
from app.schemas.food import FoodProductEntity
from app.schemas.unittype import UnitType
from app.search.client import get_search_client
from app.search.repositories.food_search_repository import FoodSearchRepository
from app.services.food_service import FoodService

OFF_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"

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

def get_nutrition(p: dict) -> NutritionEntity | None:
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

    return nutrition

def get_categories(p: dict) -> list[str]:
    categories = p.get("categories")
    if not categories:
        return []
    if isinstance(categories, str):
        return [c.strip() for c in categories.split(",") if c.strip()]
    elif isinstance(categories, list):
        return [c.strip() for c in categories if isinstance(c, str) and c.strip()]
    else:
        return []

def map_product(p: dict) -> FoodProductEntity | None:
    name = p.get("product_name") # Maybe "generic_name"
    code = p.get("code")
    quantity = p.get("quantity")
    brand = p.get("brands")

    if not name or not code:
        return None

    nutrition = get_nutrition(p)
    categories = get_categories(p)

    return FoodProductEntity(
        name=name,
        barcode=code,
        nutrition=nutrition if nutrition else NutritionEntity(),
        quantity=quantity,
        brand=brand,
        categories=categories,
    )

async def get_food_serive() -> FoodService:
    db = await get_db()
    food_repo = FoodRepository(db)

    client = await get_search_client()
    food_search_repository = FoodSearchRepository(client)

    return FoodService(food_repo=food_repo, food_search_repo=food_search_repository)

async def import_file(path: str, batch_size: int = 500):
    food_service = await get_food_serive()

    batch_by_barcode = {}

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

            # Always retain only the best product per barcode
            if code in batch_by_barcode:
                existing = batch_by_barcode[code]
                if product.completeness_score > existing.completeness_score:
                    batch_by_barcode[code] = product
            else:
                batch_by_barcode[code] = product

            if len(batch_by_barcode) >= batch_size:
                await food_service.add_products_conditional(list(batch_by_barcode.values()))
                batch_by_barcode = {}

        if batch_by_barcode:
            await food_service.add_products_conditional(list(batch_by_barcode.values()))


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
        "completeness": p.completeness_score,
        "brand": p.brand,
    }

async def main():
    url = OFF_URL
    openfoodfacts_file = settings.openfoodfacts_file
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
