from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from sqlalchemy import select
from typing import Optional
from app.db.session import get_db
from app.models.player import Player

class PlayerResponse(BaseModel):
    id: int
    name: str
    hand: str
    team: str
    pa_count: float
    avg: float
    obp: float
    slg: float
    iso: float
    k_rate: float
    bb_rate: float
    hr_rate: float
    is_rookie: str
    is_batter: bool

    class Config:
        from_attributes = True

router = APIRouter(prefix="/players", tags=["players"])

@router.get("/player-stats", response_model=list[PlayerResponse])
async def get_player_stats(
    is_batter: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Player)

    if is_batter is not None:
        query = query.where(Player.is_batter == is_batter)

    result = await db.execute(query)        # ← await here
    players = result.scalars().all()

    if not players:
        raise HTTPException(status_code=404, detail="No players found")

    return players