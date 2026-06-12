from fastapi import APIRouter, HTTPException, Query
from datetime import date, timedelta
import httpx

router = APIRouter(prefix="/schedule", tags=["schedule"])

MLB_API = "https://statsapi.mlb.com/api/v1/schedule"

@router.get("")
async def get_schedule(
    start_date: date = Query(default_factory=lambda: date.today()),
    end_date: date = Query(default_factory=lambda: date.today() + timedelta(days=6)),
):
    """
    Returns this week's MLB schedule from the official MLB Stats API.
    Defaults to today through today + 6 days if no dates are provided.
    """
    params = {
        "sportId": 1,
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(MLB_API, params=params)
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Could not reach MLB API: {e}",
            )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"MLB API error: {resp.text}",
        )

    data = resp.json()

    all_games = []

    for date_entry in data.get("dates", []):
        for game in date_entry.get("games", []):
            away_team = game["teams"]["away"]["team"]
            home_team = game["teams"]["home"]["team"]

            # Get game status
            status = game.get("status", {})
            abstract_game_state = status.get("abstractGameState", "")

            # Simple boolean for live games
            is_live = abstract_game_state in ["Live", "In Progress", "Review"]

            all_games.append({
                "gameDate": game.get("gameDate"),
                "isLive": is_live,
                "awayTeamId": away_team["id"],
                "awayTeamName": away_team["name"],
                "homeTeamId": home_team["id"],
                "homeTeamName": home_team["name"]
            })

    return {
        "totalGames": data.get("totalGames", 0),
        "games": all_games
    }
