"""
Simulation endpoints.

For now this simply forwards lineup stat arrays to the MLB model API
(`POST /simulate`) and returns its response. Later the stat arrays will be
built from the database instead of being received in the request body.
"""

import httpx
from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, conlist, field_validator

from app.config import settings
from app.limiter import limiter

router = APIRouter(prefix="/simulations", tags=["simulations"])


# ---------- Request Schema ----------
# Mirrors the model API's SimulateRequest so we get validation + Swagger docs
# before forwarding the payload as-is.

# A raw stat array = list of 10 mixed elements (str + numbers)
StatArray = conlist(object, min_length=10, max_length=10)


class SimulateRequest(BaseModel):
    """Lineup stat arrays forwarded to the model API."""

    # exactly 9 batters per team
    home_batters: conlist(StatArray, min_length=9, max_length=9)
    away_batters: conlist(StatArray, min_length=9, max_length=9)
    home_pitcher: StatArray
    away_pitcher: StatArray

    home_bullpen: Optional[list[StatArray]] = None
    away_bullpen: Optional[list[StatArray]] = None

    reliever_entry_inning: int = 6
    n_sims: Annotated[int, Field(ge=1, le=2000)] = 500
    seed: Optional[int] = None
    home_team: str = "HOME"
    away_team: str = "AWAY"
    match_id: int = 1

    @field_validator("home_batters", "away_batters", "home_pitcher", "away_pitcher")
    @classmethod
    def check_hand(cls, v):
        """stand/throws (element 0) must be L/R/S."""

        def ok(arr):
            return isinstance(arr[0], str) and arr[0] in ("L", "R", "S")

        # v may be a single array (pitcher) or a list of arrays (batters)
        arrays = v if v and isinstance(v[0], list) else [v]
        for a in arrays:
            if not ok(a):
                raise ValueError("Element 0 (stand/throws) must be 'L', 'R' or 'S'")
        return v


# ---------- Endpoints ----------
@router.post("/simulate")
@limiter.limit("30/minute")
async def simulate(request: Request, req: SimulateRequest, nested: bool = Query(False)):
    """
    Forward lineup stat arrays to the model API and return its simulation.

    The request body is passed through unchanged to `POST {MODEL_API_URL}/simulate`.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                f"{settings.MODEL_API_URL}/simulate",
                params={"nested": nested},
                json=req.model_dump(),
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
