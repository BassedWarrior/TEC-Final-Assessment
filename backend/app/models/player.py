from sqlalchemy import Column, Integer, String, Float, Boolean
from app.db.base import Base


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    hand = Column(String(1), nullable=False)  # L, R, or S
    pa = Column(Float, nullable=False)
    avg = Column(Float, nullable=False)
    obp = Column(Float, nullable=False)
    slg = Column(Float, nullable=False)
    iso = Column(Float, nullable=False)
    k_rate = Column(Float, nullable=False)
    bb_rate = Column(Float, nullable=False)
    hr_rate = Column(Float, nullable=False)
    is_rookie = Column(String, nullable=False)
    is_batter = Column(Boolean, nullable=False)
