"""
Lineup assembly middleware.

Bridges the ID-based request the frontend sends and the stat-array payload the
model API expects: given player ids, it pulls each player's stat line from the
'players' table and rebuilds the 10-element arrays (in lineup order) that the
Monte Carlo simulator consumes.

If any requested id is absent from the table the whole request fails with 422,
listing the missing ids (no silent imputation).
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player


async def _fetch_stat_arrays(db: AsyncSession, ids: list[int]) -> dict[int, list]:
    """
    Resolve a set of player ids to their stat arrays in a single query.

    Returns {id: stat_array}. Raises 422 if any id is missing from the table.
    """
    unique_ids = list(dict.fromkeys(ids))  # de-dupe, preserve order

    result = await db.execute(select(Player).where(Player.id.in_(unique_ids)))
    by_id = {p.id: p.to_stat_array() for p in result.scalars().all()}

    missing = [pid for pid in unique_ids if pid not in by_id]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Player ids not found in database: {missing}",
        )
    return by_id


def _arrays_for(ids: list[int], by_id: dict[int, list]) -> list[list]:
    """Map a list of ids to their stat arrays, preserving the given order."""
    return [by_id[pid] for pid in ids]


async def build_model_payload(
    db: AsyncSession,
    *,
    home_batter_ids: list[int],
    away_batter_ids: list[int],
    home_pitcher_id: int,
    away_pitcher_id: int,
    home_bullpen_ids: Optional[list[int]] = None,
    away_bullpen_ids: Optional[list[int]] = None,
    reliever_entry_inning: int = 6,
    n_sims: int = 500,
    seed: Optional[int] = None,
    home_team: str = "HOME",
    away_team: str = "AWAY",
    match_id: int = 1,
) -> dict:
    """
    Turn an ID-based lineup request into the stat-array payload the model API
    expects (mirrors the model API's SimulateRequest schema).
    """
    home_bullpen_ids = home_bullpen_ids or []
    away_bullpen_ids = away_bullpen_ids or []

    # One DB round-trip for every player involved.
    all_ids = (
        home_batter_ids
        + away_batter_ids
        + [home_pitcher_id, away_pitcher_id]
        + home_bullpen_ids
        + away_bullpen_ids
    )
    by_id = await _fetch_stat_arrays(db, all_ids)

    return {
        "home_batters": _arrays_for(home_batter_ids, by_id),
        "away_batters": _arrays_for(away_batter_ids, by_id),
        "home_pitcher": by_id[home_pitcher_id],
        "away_pitcher": by_id[away_pitcher_id],
        "home_bullpen": _arrays_for(home_bullpen_ids, by_id) or None,
        "away_bullpen": _arrays_for(away_bullpen_ids, by_id) or None,
        "reliever_entry_inning": reliever_entry_inning,
        "n_sims": n_sims,
        "seed": seed,
        "home_team": home_team,
        "away_team": away_team,
        "match_id": match_id,
    }
