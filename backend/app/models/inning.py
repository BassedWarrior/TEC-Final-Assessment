from sqlalchemy import Column, Integer, ForeignKey
from app.db.base import Base


class Inning(Base):
    __tablename__ = "innings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=False)
    inning_number = Column(Integer, nullable=False)
    home_stko = Column(Integer, nullable=False)
    away_stko = Column(Integer, nullable=False)
    home_hits = Column(Integer, nullable=False)
    away_hits = Column(Integer, nullable=False)
    home_runs = Column(Integer, nullable=False)
    away_runs = Column(Integer, nullable=False)
    home_hr = Column(Integer, nullable=False)
    away_hr = Column(Integer, nullable=False)
