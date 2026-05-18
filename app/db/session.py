from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(
    settings.database_url_async,
    # echo=True,  # turn off in prod
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
