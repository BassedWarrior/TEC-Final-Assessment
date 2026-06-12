"""
Simulation endpoints.

`POST /simulations/simulate` receives player *ids* for both lineups. A middleware
service (`app.services.lineups`) relates each id to its stat line in the
'players' table and rebuilds the stat arrays the model API expects. The model's
per-simulation output is then aggregated into per-inning and whole-game averages
(`app.services.results`), stored in the `matches` / `match_innings` tables, and
the endpoint returns the id of the persisted match.
"""

import httpx
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, conlist
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.session import get_db
from app.models.match import Match, MatchInning
from app.models.user import User
from app.services.lineups import build_model_payload
from app.services.results import aggregate_results
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/simulations", tags=["simulations"])

# Whole-game / per-inning average column names (shared by serialization).
_AVG_FIELDS = (
    "avg_home_runs",
    "avg_away_runs",
    "avg_home_hits",
    "avg_away_hits",
    "avg_home_hr",
    "avg_away_hr",
    "avg_home_strikeouts",
    "avg_away_strikeouts",
)


# ---------- Request Schema ----------
# The frontend sends ids only; stats are resolved from the database.


class SimulateRequest(BaseModel):
    """Lineup player ids, resolved to stat arrays before hitting the model API."""

    # exactly 9 batters per team
    home_batter_ids: conlist(int, min_length=9, max_length=9)
    away_batter_ids: conlist(int, min_length=9, max_length=9)
    home_pitcher_id: int
    away_pitcher_id: int

    home_bullpen_ids: Optional[list[int]] = None
    away_bullpen_ids: Optional[list[int]] = None

    reliever_entry_inning: int = 6
    n_sims: Annotated[int, Field(ge=1, le=2000)] = 500
    seed: Optional[int] = None
    home_team: str = "HOME"
    away_team: str = "AWAY"


# ---------- Endpoints ----------
@router.post("/simulate", status_code=201)
async def simulate(
    req: SimulateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Resolve player ids, run the simulation, persist the aggregated result.

    Returns the id of the stored match: ``{"match_id": <int>}``.
    """
    payload = await build_model_payload(
        db,
        home_batter_ids=req.home_batter_ids,
        away_batter_ids=req.away_batter_ids,
        home_pitcher_id=req.home_pitcher_id,
        away_pitcher_id=req.away_pitcher_id,
        home_bullpen_ids=req.home_bullpen_ids,
        away_bullpen_ids=req.away_bullpen_ids,
        reliever_entry_inning=req.reliever_entry_inning,
        n_sims=req.n_sims,
        seed=req.seed,
        home_team=req.home_team,
        away_team=req.away_team,
    )

    # Ask the model for the flat per-inning breakdown (needed to aggregate).
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                f"{settings.MODEL_API_URL}/simulate",
                params={"nested": False},
                json=payload,
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Could not reach model API at {settings.MODEL_API_URL}: {e}",
            )

    if resp.status_code != 200:
        # Surface the model API's error to the caller
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    agg = aggregate_results(resp.json())

    # Persist match-level averages + per-inning averages.
    match = Match(
        user_id=user.id,
        home_team=req.home_team,
        away_team=req.away_team,
        n_sims=agg["total_sims"],
        home_wp=agg["home_wp"],
        away_wp=agg["away_wp"],
        **agg["whole_game"],
    )
    match.innings = [MatchInning(**row) for row in agg["innings"]]

    db.add(match)
    await db.commit()
    await db.refresh(match)

    return {"match_id": match.id}


@router.get("/{match_id}")
async def get_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Return a stored match: win probabilities, whole-game averages and the
    per-inning average breakdown. Only the match's owner can read it.
    """
    result = await db.execute(
        select(Match)
        .where(Match.id == match_id)
        .options(selectinload(Match.innings))
    )
    match = result.scalar_one_or_none()

    # 404 (not 403) when it belongs to someone else, so we don't leak existence.
    if match is None or match.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Match not found"
        )

    return {
        "match_id": match.id,
        "created_at": match.created_at.isoformat() if match.created_at else None,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "n_sims": match.n_sims,
        "home_wp": match.home_wp,
        "away_wp": match.away_wp,
        "whole_game": {f: getattr(match, f) for f in _AVG_FIELDS},
        "innings": [
            {"inning_number": inn.inning_number, **{f: getattr(inn, f) for f in _AVG_FIELDS}}
            for inn in match.innings
        ],
    }
