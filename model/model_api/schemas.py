from typing import Annotated, Optional, Dict
from pydantic import BaseModel, Field, RootModel, conlist, field_validator

# Un array crudo = lista de 10 elementos mixtos (str + números)
StatArray = conlist(object, min_length=10, max_length=10)


class SimulateRequest(BaseModel):
    # exactamente 9 bateadores por equipo
    home_batters: conlist(StatArray, min_length=9, max_length=9)
    away_batters: conlist(StatArray, min_length=9, max_length=9)
    home_pitcher: StatArray
    away_pitcher: StatArray

    home_bullpen: Optional[list[StatArray]] = None
    away_bullpen: Optional[list[StatArray]] = None

    reliever_entry_inning: int = 6
    n_sims: Annotated[int, Field(ge=1, le=2000)] = 500
    seed: Optional[int] = None
    home_team: str = "HOME"
    away_team: str = "AWAY"

    @field_validator("home_batters", "away_batters", "home_pitcher", "away_pitcher")
    @classmethod
    def check_hand(cls, v):
        """stand/throws (elemento 0) debe ser L/R/S."""
        def ok(arr):
            return isinstance(arr[0], str) and arr[0] in ("L", "R", "S")
        # v puede ser un array (pitcher) o lista de arrays (batters)
        arrays = v if v and isinstance(v[0], list) else [v]
        for a in arrays:
            if not ok(a):
                raise ValueError("El elemento 0 (stand/throws) debe ser 'L', 'R' o 'S'")
        return v


# ---------- Response models (nested format) ----------
class InningStats(BaseModel):
    """Statistics for one inning."""

    Home_STKO: float = Field(..., alias="Home_STKO", description="Home strikeouts")
    Away_STKO: float = Field(..., alias="Away_STKO", description="Away strikeouts")
    Home_Hits: float = Field(..., alias="Home_Hits", description="Home hits")
    Away_Hits: float = Field(..., alias="Away_Hits", description="Away hits")
    Home_Runs: float = Field(..., alias="Home_Runs", description="Home runs scored")
    Away_Runs: float = Field(..., alias="Away_Runs", description="Away runs scored")
    Home_HR: float = Field(..., alias="Home_HR", description="Home home runs")
    Away_HR: float = Field(..., alias="Away_HR", description="Away home runs")

    model_config = {
        "validate_by_name": True,
        "json_schema_extra": {
            "example": {
                "Home_STKO": 2.5,
                "Away_STKO": 3.0,
                "Home_Hits": 1.2,
                "Away_Hits": 0.8,
                "Home_Runs": 0.5,
                "Away_Runs": 0.2,
                "Home_HR": 0.1,
                "Away_HR": 0.0,
            }
        }


class SimulationDetail(RootModel):
    """A single simulation: mapping inning_N -> InningStats."""

    root: Dict[str, InningStats] = Field(
        ...,
        description="Dictionary with keys 'inning_1', 'inning_2', ...",
    )

    def __getitem__(self, key):
        return self.root[key]

    def __iter__(self):
        return iter(self.root)


class SimulateResponseNested(BaseModel):
    Home_wp: float = Field(..., description="Home team win probability", ge=0, le=1)
    Away_wp: float = Field(..., description="Away team win probability", ge=0, le=1)
    Simulations: Dict[str, SimulationDetail] = Field(
        ..., description="Dictionary sim_1, sim_2, ... with inning details"
    )
