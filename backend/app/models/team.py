"""
Team model.

Maps the 'teams' table: one row per MLB club, keyed by its official MLB Stats
API team id. `lineup_id` is a group identifier shared by every `lineups` row
that belongs to this team's roster (see app.models.lineup); a team owns many
lineup slots (batters + pitchers), all tagged with the same lineup_id.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Team(Base):
    """One MLB club, keyed by its official MLB team id."""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, autoincrement=False)  # official MLB team id
    name = Column(String, nullable=False)  # team full name, e.g. "Los Angeles Dodgers"
    lineup_id = Column(Integer, nullable=False)  # group id shared by this team's lineups rows

    lineup = relationship(
        "Lineup",
        back_populates="team",
        cascade="all, delete-orphan",
        order_by="Lineup.batting_order",
    )
