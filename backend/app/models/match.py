"""
Match models.

Persist the aggregated outcome of a simulated game:
  - `matches`        : one row per simulation request — win probabilities and
                       whole-game average runs/hits/HR/strikeouts per team.
  - `match_innings`  : one row per inning of that match — the same averages
                       broken down by inning_number.

The auto-incrementing `matches.id` is what the /simulate endpoint returns.
Averages are computed in app.services.results.aggregate_results.
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Date, Time, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Match(Base):
    """Match-level aggregates (win prob + whole-game averages)."""

    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, autoincrement=True)  # serial id returned to the client
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # When the real-world game is scheduled to start, split into date and time
    # (UTC, from the MLB schedule). NULL for ad-hoc user simulations; set by the
    # schedule cron (app.db.scripts.download_matches) for pre-simulated games.
    match_date = Column(Date, nullable=True, index=True)
    match_time = Column(Time, nullable=True)

    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)

    home_wp = Column(Float, nullable=False)
    away_wp = Column(Float, nullable=False)
    n_sims = Column(Integer, nullable=False)

    # Whole-game averages (per team)
    avg_home_runs = Column(Float, nullable=False)
    avg_away_runs = Column(Float, nullable=False)
    avg_home_hits = Column(Float, nullable=False)
    avg_away_hits = Column(Float, nullable=False)
    avg_home_hr = Column(Float, nullable=False)
    avg_away_hr = Column(Float, nullable=False)
    avg_home_strikeouts = Column(Float, nullable=False)
    avg_away_strikeouts = Column(Float, nullable=False)

    innings = relationship(
        "MatchInning",
        back_populates="match",
        cascade="all, delete-orphan",
        order_by="MatchInning.inning_number",
    )

    # The exact rosters this match ran with — one row per lineup slot. Mirrors the
    # team-roster `lineups` table, but scoped to a match (and a home/away side)
    # instead of a team. Lets the history view rebuild the lineups the user built.
    lineup_slots = relationship(
        "MatchLineup",
        back_populates="match",
        cascade="all, delete-orphan",
        order_by="MatchLineup.slot_order",
    )


class MatchInning(Base):
    """Per-inning averages for a match."""

    __tablename__ = "match_innings"

    id = Column(Integer, primary_key=True)
    match_id = Column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inning_number = Column(Integer, nullable=False)

    avg_home_runs = Column(Float, nullable=False)
    avg_away_runs = Column(Float, nullable=False)
    avg_home_hits = Column(Float, nullable=False)
    avg_away_hits = Column(Float, nullable=False)
    avg_home_hr = Column(Float, nullable=False)
    avg_away_hr = Column(Float, nullable=False)
    avg_home_strikeouts = Column(Float, nullable=False)
    avg_away_strikeouts = Column(Float, nullable=False)

    match = relationship("Match", back_populates="innings")


class MatchLineup(Base):
    """One player slot (batter or pitcher) within a match's home/away lineup.

    Same shape as the team `lineups` table — `is_batter` tells batters from
    pitchers and `slot_order` is the position within that group — but keyed to a
    match and a side rather than a team. Pitcher slot 1 is the starter; higher
    slot numbers are the bullpen.
    """

    __tablename__ = "match_lineups"

    id = Column(Integer, primary_key=True)
    match_id = Column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    side = Column(String(4), nullable=False)  # "home" or "away"
    is_batter = Column(Boolean, nullable=False)  # True = batter, False = pitcher
    slot_order = Column(Integer, nullable=False)  # position within its side+role group
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)

    match = relationship("Match", back_populates="lineup_slots")
