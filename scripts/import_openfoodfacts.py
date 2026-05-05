import gzip
import json
from uuid import uuid4
import os
import requests
from pathlib import Path
import asyncio
from pathlib import Path
from tqdm import tqdm

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FoodProductDB
from app.db.session import AsyncSessionLocal

OFF_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"


def map_product(p: dict) -> FoodProductDB | None:
    name = p.get("product_name")
    code = p.get("code")

    if not name or not code:
        return None

    nutriments = p.get("nutriments", {})

    nutrition = {
        "calories": nutriments.get("energy-kcal_100g"),
        "protein": nutriments.get("proteins_100g"),
        "fat": nutriments.get("fat_100g"),
        "carbs": nutriments.get("carbohydrates_100g"),
    }

    return FoodProductDB(
        id=uuid4(),
        name=name,
        barcode=code,
        nutrition=nutrition,
    )

async def insert_batch(session: AsyncSession, batch: list[FoodProductDB]):
    session.add_all(batch)
    await session.flush()
    await session.commit()

async def import_file(path: str, batch_size: int = 500):
    batch = []

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

                batch.append(product)

                if len(batch) >= batch_size:
                    await insert_batch(session, batch)
                    batch = []

            if batch:
                await insert_batch(session, batch)

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

    # print("Downloading dataset...")
    # download_file(url, file_path)

    print("Importing into database...")
    await import_file(str(file_path))

    print("Cleaning up...")
    file_path.unlink()  # deletes file

    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
