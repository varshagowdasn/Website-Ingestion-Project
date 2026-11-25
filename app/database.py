import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
os.makedirs("./data", exist_ok=True)
engine = create_async_engine(settings.database_url)
Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
async def get_db():
    async with Session() as session:
        yield session
async def init_db():
    from app.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
