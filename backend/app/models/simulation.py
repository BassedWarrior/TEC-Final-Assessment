from sqlalchemy import Column, Integer, Float, ForeignKey
from app.db.base import Base


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    avg_home_stko = Column(Float, nullable=False)
    avg_away_stko = Column(Float, nullable=False)
    avg_home_hits = Column(Float, nullable=False)
    avg_away_hits = Column(Float, nullable=False)
    avg_home_runs = Column(Float, nullable=False)
    avg_away_runs = Column(Float, nullable=False)
    avg_home_hr = Column(Float, nullable=False)
    avg_away_hr = Column(Float, nullable=False)
