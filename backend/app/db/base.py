"""
Database engine and session factory.

Creates async SQLAlchemy engine using the DATABASE_URL from settings.
Defines the declarative Base class for all ORM models and a dependency
function 'get_db' to be used in FastAPI endpoints.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    """
    Dependency that provides an async database session.

    Yields:
        AsyncSession: SQLAlchemy async session.
    """
    async with AsyncSessionLocal() as session:
        yield session
