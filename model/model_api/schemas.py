from typing import Annotated, Optional
from pydantic import BaseModel, Field, conlist, field_validator

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
