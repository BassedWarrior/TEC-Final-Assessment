"""Drop and recreate the public schema (CASCADE).

Usage (from the backend/ directory):
    python -m app.db.scripts.drop_db

WARNING: Destroys ALL data and tables. Development use only.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy import text
from app.db.base import engine


async def drop():
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    print("Schema dropped and recreated. Run init_db to recreate tables.")


if __name__ == "__main__":
    asyncio.run(drop())
