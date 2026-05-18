from meilisearch import Client
from core.config import settings

client = Client(
    settings.meili_url,
    settings.meili_master_key,
)

async def get_search_client() -> Client:
    return client
