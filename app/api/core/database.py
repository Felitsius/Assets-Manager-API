from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from typing import AsyncGenerator

from app.api.core.config import SYNC_DATABASE_URL, ASYNC_DATABASE_URL

sync_engine = create_engine(SYNC_DATABASE_URL, echo=True, future=True)

async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=True, future=True)

SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

def get_db():
    """Функция для получения синхронной сессии"""

    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Функция для получения асинхронной сессии"""
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()