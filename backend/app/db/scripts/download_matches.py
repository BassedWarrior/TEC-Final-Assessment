"""
Download the upcoming MLB schedule and persist each game as a pre-simulated Match.

Meant to run on a schedule (cron). For every game in the requested window it:
  1. resolves both clubs' default rosters from `teams` / `lineups`,
  2. runs the Monte Carlo simulation through the model API,
  3. stores the aggregated result in `matches` (+ `match_innings`, `match_lineups`),
     stamped with `match_at` — the real-world start time from the MLB schedule.

Cron-created matches carry `user_id = NULL` (they belong to no user, so they never
show up in a user's `/simulations/history`). Re-running is safe: a game already
persisted for the same teams and `match_at` is skipped rather than duplicated.

Usage (from the backend/ directory):
    python -m app.db.scripts.download_matches               # today's games
    python -m app.db.scripts.download_matches 2026-06-12    # a specific day
"""

import asyncio
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # adds backend/ to path

from dotenv import load_dotenv

load_dotenv()

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.base import engine
from app.models.lineup import Lineup
from app.models.match import Match, MatchInning, MatchLineup
from app.models.player import Player  # noqa: F401 — registers `players` for FK resolution
from app.models.team import Team
from app.models.user import User  # noqa: F401 — registers `users` for FK resolution
from app.services.lineups import build_model_payload
from app.services.results import aggregate_results

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

MLB_API = "https://statsapi.mlb.com/api/v1/schedule"
N_SIMS = 100  # simulations per game (kept low: the cron simulates the whole week)


async def _fetch_schedule(day: date) -> list[dict]:
    """Return the games scheduled on `day`.

    Each entry: home/away MLB team ids and the tz-aware start datetime.
    """
    params = {"sportId": 1, "startDate": day.isoformat(), "endDate": day.isoformat()}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(MLB_API, params=params)
    resp.raise_for_status()

    games = []
    for date_entry in resp.json().get("dates", []):
        for game in date_entry.get("games", []):
            game_date = game.get("gameDate", "")
            if not game_date:
                continue
            games.append(
                {
                    "home_team_id": game["teams"]["home"]["team"]["id"],
                    "away_team_id": game["teams"]["away"]["team"]["id"],
                    "starts_at": datetime.fromisoformat(game_date.replace("Z", "+00:00")),
                }
            )
    return games


async def _team_lineup(db: AsyncSession, team_id: int) -> tuple[Team, list[int], list[int]]:
    """Resolve a club's default lineup to (team, batter_ids, pitcher_ids).

    batter_ids are in batting order; pitcher_ids[0] is the starter, the rest the
    bullpen. Raises LookupError if the team or a complete lineup is missing.
    """
    team = await db.get(Team, team_id)
    if team is None:
        raise LookupError(f"team id {team_id} not in `teams`")

    rows = (
        await db.execute(
            select(Lineup)
            .where(Lineup.lineup_id == team.lineup_id)
            .order_by(Lineup.batting_order)
        )
    ).scalars().all()

    batter_ids = [r.player_id for r in rows if r.is_batter]
    pitcher_ids = [r.player_id for r in rows if not r.is_batter]
    if len(batter_ids) < 9 or not pitcher_ids:
        raise LookupError(
            f"{team.name}: incomplete lineup "
            f"({len(batter_ids)} batters, {len(pitcher_ids)} pitchers)"
        )
    return team, batter_ids[:9], pitcher_ids


def _build_lineup_slots(
    home_batters: list[int],
    away_batters: list[int],
    home_pitchers: list[int],
    away_pitchers: list[int],
) -> list[MatchLineup]:
    """Flatten resolved lineups into per-slot MatchLineup rows (starter = slot 1)."""
    groups = [
        ("home", True, home_batters),
        ("away", True, away_batters),
        ("home", False, home_pitchers),
        ("away", False, away_pitchers),
    ]
    return [
        MatchLineup(side=side, is_batter=is_batter, slot_order=i, player_id=pid)
        for side, is_batter, ids in groups
        for i, pid in enumerate(ids, start=1)
    ]


async def _already_persisted(db: AsyncSession, home: str, away: str, starts_at: datetime) -> bool:
    """True if this game (same teams + start date/time) was already downloaded."""
    existing = await db.execute(
        select(Match.id).where(
            Match.home_team == home,
            Match.away_team == away,
            Match.match_date == starts_at.date(),
            Match.match_time == starts_at.time(),
        )
    )
    return existing.first() is not None


async def _simulate_and_store(db: AsyncSession, client: httpx.AsyncClient, game: dict) -> str:
    """Pre-simulate one scheduled game and persist it. Returns a status string."""
    starts_at = game["starts_at"]
    home_team, home_batters, home_pitchers = await _team_lineup(db, game["home_team_id"])
    away_team, away_batters, away_pitchers = await _team_lineup(db, game["away_team_id"])

    if await _already_persisted(db, home_team.name, away_team.name, starts_at):
        return f"skip (exists): {away_team.name} @ {home_team.name}"

    payload = await build_model_payload(
        db,
        home_batter_ids=home_batters,
        away_batter_ids=away_batters,
        home_pitcher_id=home_pitchers[0],
        away_pitcher_id=away_pitchers[0],
        home_bullpen_ids=home_pitchers[1:],
        away_bullpen_ids=away_pitchers[1:],
        n_sims=N_SIMS,
        home_team=home_team.name,
        away_team=away_team.name,
    )

    resp = await client.post(f"{settings.MODEL_API_URL}/simulate", json=payload)
    resp.raise_for_status()
    agg = aggregate_results(resp.json())

    match = Match(
        user_id=None,
        match_date=starts_at.date(),
        match_time=starts_at.time(),
        home_team=home_team.name,
        away_team=away_team.name,
        n_sims=agg["total_sims"],
        home_wp=agg["home_wp"],
        away_wp=agg["away_wp"],
        **agg["whole_game"],
    )
    match.innings = [MatchInning(**row) for row in agg["innings"]]
    match.lineup_slots = _build_lineup_slots(
        home_batters, away_batters, home_pitchers, away_pitchers
    )

    db.add(match)
    await db.commit()
    return f"saved: {away_team.name} @ {home_team.name} ({starts_at:%Y-%m-%d %H:%M}Z)"


async def download(day: date) -> None:
    games = await _fetch_schedule(day)
    print(f"{len(games)} scheduled game(s) on {day}")

    saved = skipped = failed = 0
    async with AsyncSessionLocal() as db, httpx.AsyncClient(timeout=120.0) as client:
        for game in games:
            try:
                status = await _simulate_and_store(db, client, game)
                skipped += status.startswith("skip")
                saved += status.startswith("saved")
                print(f"  {status}")
            except (LookupError, httpx.HTTPError) as e:
                failed += 1
                await db.rollback()
                print(f"  skip (error): {e}")

    print(f"done: {saved} saved, {skipped} already present, {failed} failed")


if __name__ == "__main__":
    target_day = date.fromisoformat(sys.argv[1]) if len(sys.argv) == 2 else date.today()
    asyncio.run(download(target_day))
