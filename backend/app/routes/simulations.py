"""
Simulation endpoints.

The endpoint receives player *ids* for both lineups. A middleware service
(`app.services.lineups`) relates each id to its stat line stored in the
'players' table and rebuilds the stat arrays the model API expects, then the
assembled payload is forwarded to the MLB model API (`POST /simulate`).
"""

import httpx
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, conlist
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.services.lineups import build_model_payload

router = APIRouter(prefix="/simulations", tags=["simulations"])


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
    match_id: int = 1


# ---------- Endpoints ----------
@router.post("/simulate")
async def simulate(
    req: SimulateRequest,
    nested: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve player ids to stat arrays, then forward the lineup to the model API.

    The assembled stat-array payload is sent to `POST {MODEL_API_URL}/simulate`.
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
        match_id=req.match_id,
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                f"{settings.MODEL_API_URL}/simulate",
                params={"nested": nested},
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

    return resp.json()
