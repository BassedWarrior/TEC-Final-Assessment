"""One-Time DataBase initialization script.

Usage (from the backend/ directory):
    python -m app.db.scripts.init_db

Creates all tables defined in SQLAlchemy models if they don't already exist.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # adds backend/ to path

from app.db.base import engine, Base

# Import all models so Base knows about them
from app.models.user import User  # noqa: F401
from app.models.player import Player  # noqa: F401
from app.models.team import Team  # noqa: F401
from app.models.lineup import Lineup  # noqa: F401
from app.models.match import Match  # noqa: F401
from app.models.simulation import Simulation  # noqa: F401
from app.models.inning import Inning  # noqa: F401


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init())
