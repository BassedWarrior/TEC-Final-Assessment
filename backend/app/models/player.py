"""
Player model.

Maps the 'players' table: one row per MLBAM player id holding the season stat
line consumed by the Monte Carlo simulator. The same columns serve both batters
and pitchers; whether a row is read as a batter or pitcher stat array depends on
which lineup slot the id is requested in (see app.services.lineups).

Column order mirrors BATTER_ARRAY_FIELDS / PITCHER_ARRAY_FIELDS in
model/download_data/mlb_stats.py so the assembled array matches what the model
API expects.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean
from app.db.base import Base


class Player(Base):
    """Per-player season stat line, keyed by MLBAM id."""

    __tablename__ = "players"

    id = Column(Integer, primary_key=True, autoincrement=True)  # MLBAM player id
    name = Column(String, nullable=False)
    hand = Column(String(1), nullable=False)  # stand/throws: "L", "R" or "S"
    pa_count = Column(Float, nullable=False)
    avg = Column(Float, nullable=False)
    obp = Column(Float, nullable=False)
    slg = Column(Float, nullable=False)
    iso = Column(Float, nullable=False)
    k_rate = Column(Float, nullable=False)
    bb_rate = Column(Float, nullable=False)
    hr_rate = Column(Float, nullable=False)
    is_rookie = Column(String, nullable=False)
    is_batter = Column(Boolean, nullable=False)

    def to_stat_array(self) -> list:
        """Return the 10-element stat array in BATTER/PITCHER_ARRAY_FIELDS order."""
        return [
            self.hand,
            float(self.pa_count),
            self.avg,
            self.obp,
            self.slg,
            self.iso,
            self.k_rate,
            self.bb_rate,
            self.hr_rate,
            int(self.is_rookie),
        ]
