"""
Lineup model.

Maps the 'lineups' table: one row per player slot in a team's roster. A single
team's lineup is the set of rows sharing the same `lineup_id` (which mirrors
teams.lineup_id) — it holds BOTH the batting order and the pitching staff, told
apart by the `is_batter` flag (True = batter, False = pitcher), matching the
same convention on the players table. `batting_order` is the slot position
within the lineup; `player_id` points at the MLBAM player id in players.
"""

from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class Lineup(Base):
    """One player slot (batter or pitcher) within a team's lineup."""

    __tablename__ = "lineups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lineup_id = Column(Integer, nullable=False, index=True)  # group id, mirrors teams.lineup_id
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    batting_order = Column(Integer, nullable=False)  # slot position within the lineup
    is_batter = Column(Boolean, nullable=False)  # True = batter, False = pitcher
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)

    team = relationship("Team", back_populates="lineup")
