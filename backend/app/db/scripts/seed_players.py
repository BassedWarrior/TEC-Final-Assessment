"""
Seed the `players` table from official MLB stats (statsapi.mlb.com).

Usage (from the backend/ directory):
    python -m app.db.scripts.seed_players [season]   # season defaults to 2026
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # adds backend/ to path
# Make mlb_stats importable (backend/app/db/scripts/ -> repo root -> model/download_data/)
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "model" / "download_data"))
import mlb_stats

from dotenv import load_dotenv
load_dotenv()

from app.db.base import engine
from app.models.player import Player
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

SEASON = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
MIN_PA_BATTER = 100
MIN_PA_PITCHER = 50


def _names_from_splits(group: str, season: int) -> dict:
    return {
        s["player"]["id"]: s["player"].get("fullName", str(s["player"]["id"]))
        for s in mlb_stats._fetch_season_splits(group, season)
    }


async def seed():
    print(f"Fetching MLB stats for {SEASON}...")
    batters = mlb_stats.batter_frame(SEASON)
    pitchers = mlb_stats.pitcher_frame(SEASON)

    batter_names = _names_from_splits("hitting", SEASON)
    pitcher_names = _names_from_splits("pitching", SEASON)

    all_ids = list(batters.index) + list(pitchers.index)
    print(f"Fetching handedness for {len(all_ids)} players...")
    hands = mlb_stats._handedness(all_ids)

    seen_ids = set()
    players = []

    for mlb_id, row in batters.iterrows():
        seen_ids.add(int(mlb_id))
        is_rookie = row["pa_count"] < MIN_PA_BATTER
        players.append(Player(
            id=int(mlb_id),
            name=batter_names.get(mlb_id, str(mlb_id)),
            hand=hands.get(mlb_id, {}).get("bat", "R"),
            pa_count=float(row["pa_count"]),
            avg=row["avg"], obp=row["obp"], slg=row["slg"], iso=row["iso"],
            k_rate=row["k_rate"], bb_rate=row["bb_rate"], hr_rate=row["hr_rate"],
            is_rookie="1" if is_rookie else "0",
            is_batter=True,
        ))

    for mlb_id, row in pitchers.iterrows():
        if int(mlb_id) in seen_ids:
            continue
        is_rookie = row["pa_count"] < MIN_PA_PITCHER
        players.append(Player(
            id=int(mlb_id),
            name=pitcher_names.get(mlb_id, str(mlb_id)),
            hand=hands.get(mlb_id, {}).get("throw", "R"),
            pa_count=float(row["pa_count"]),
            avg=row["avg"], obp=row["obp"], slg=row["slg"], iso=row["iso"],
            k_rate=row["k_rate"], bb_rate=row["bb_rate"], hr_rate=row["hr_rate"],
            is_rookie="1" if is_rookie else "0",
            is_batter=False,
        ))

    async with AsyncSessionLocal() as db:
        await db.execute(text("TRUNCATE TABLE players RESTART IDENTITY CASCADE"))
        db.add_all(players)
        await db.commit()

    print(f"Seeded {len(batters)} batters and {len(pitchers)} pitchers ({len(players)} total).")


asyncio.run(seed())
