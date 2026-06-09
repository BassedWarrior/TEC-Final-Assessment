from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
 
import numpy as np
import pandas as pd
import lightgbm as lgb

from GameState import GameState, Outcome


DATA_DIR = Path("./data")
MODELS_DIR = Path("./models")
 
# Orden de las clases (debe matchear el modelo entrenado)
OUTCOME_ORDER = ["K", "BB", "HBP", "1B", "2B", "3B", "HR", "OUT", "DP", "SF"]
OUTCOME_FROM_INDEX = {
    0: Outcome.STRIKEOUT,
    1: Outcome.WALK,
    2: Outcome.HIT_BY_PITCH,
    3: Outcome.SINGLE,
    4: Outcome.DOUBLE,
    5: Outcome.TRIPLE,
    6: Outcome.HOME_RUN,
    7: Outcome.OUT_IN_PLAY,
    8: Outcome.DOUBLE_PLAY,
    9: Outcome.SAC_FLY,
}

LEAGUE_AVG = {
    "avg":     0.243, "obp":     0.312, "slg":     0.399, "iso":     0.156,
    "k_rate":  0.226, "bb_rate": 0.082, "hr_rate": 0.029,
}

@dataclass
class BatterProfile:
    """Stats de un bateador (las features que espera el modelo)."""
    batter_id: int
    stand: str  # "L", "R", o "S"
    pa_count: float
    avg: float
    obp: float
    slg: float
    iso: float
    k_rate: float
    bb_rate: float
    hr_rate: float
    is_rookie: bool = False
 
 
@dataclass
class PitcherProfile:
    """Stats de un pitcher (las features que espera el modelo)."""
    pitcher_id: int
    throws: str  # "L" o "R"
    pa_count: float
    avg: float
    obp: float
    slg: float
    iso: float
    k_rate: float
    bb_rate: float
    hr_rate: float
    is_new: bool = False
 
 
@dataclass
class TeamLineup:
    team_name: str
    batters: list[BatterProfile]  # exactamente 9
    pitcher: PitcherProfile        # abridor
    bullpen: list[PitcherProfile] = field(default_factory=list)  # relevistas
    reliever_entry_inning: int = 6  # inning en que entra el primer relevista

    def __post_init__(self):
        if len(self.batters) != 9:
            raise ValueError(f"Lineup necesita 9 bateadores, tiene {len(self.batters)}")

    def batter_at(self, idx: int) -> BatterProfile:
        return self.batters[idx]

    def pitcher_for_inning(self, inning: int) -> PitcherProfile:
        """
        Devuelve el pitcher activo para el inning dado.

        El abridor lanza hasta `reliever_entry_inning - 1`. A partir de ese
        inning entra el bullpen: el primer relevista en el inning de entrada,
        el siguiente un inning después, etc. Si solo hay un relevista, este
        cubre todos los innings restantes.
        """
        if not self.bullpen or inning < self.reliever_entry_inning:
            return self.pitcher
        idx = min(inning - self.reliever_entry_inning, len(self.bullpen) - 1)
        return self.bullpen[idx]
    
def build_player_profiles(pa_2024: pd.DataFrame) -> tuple[dict, dict]:
    
    # Bateadores
    df = pa_2024.copy()
    df["is_hit"] = df["pa_outcome"].isin(["1B", "2B", "3B", "HR"]).astype(int)
    df["is_K"]   = (df["pa_outcome"] == "K").astype(int)
    df["is_BB"]  = (df["pa_outcome"] == "BB").astype(int)
    df["is_HBP"] = (df["pa_outcome"] == "HBP").astype(int)
    df["is_HR"]  = (df["pa_outcome"] == "HR").astype(int)
    df["total_bases"] = (
        (df["pa_outcome"] == "1B").astype(int) +
        2 * (df["pa_outcome"] == "2B").astype(int) +
        3 * (df["pa_outcome"] == "3B").astype(int) +
        4 * df["is_HR"]
    )
 
    batter_profiles = {}
    for batter_id, group in df.groupby("batter"):
        pa_count = len(group)
        at_bats = max(pa_count - group["is_BB"].sum() - group["is_HBP"].sum(), 1)
        hits = group["is_hit"].sum()
 
        # Mano: tomamos el modo (la mano más común con la que bateó)
        stand = group["stand"].mode().iloc[0] if not group["stand"].mode().empty else "R"
 
        batter_profiles[batter_id] = BatterProfile(
            batter_id=batter_id,
            stand=stand,
            pa_count=pa_count,
            avg=hits / at_bats,
            obp=(hits + group["is_BB"].sum() + group["is_HBP"].sum()) / pa_count,
            slg=group["total_bases"].sum() / at_bats,
            iso=(group["total_bases"].sum() / at_bats) - (hits / at_bats),
            k_rate=group["is_K"].sum() / pa_count,
            bb_rate=group["is_BB"].sum() / pa_count,
            hr_rate=group["is_HR"].sum() / pa_count,
            is_rookie=False,
        )
 
    # Pitchers (misma lógica, agrupado por pitcher)
    pitcher_profiles = {}
    for pitcher_id, group in df.groupby("pitcher"):
        pa_count = len(group)
        at_bats = max(pa_count - group["is_BB"].sum() - group["is_HBP"].sum(), 1)
        hits = group["is_hit"].sum()
 
        throws = group["p_throws"].mode().iloc[0] if not group["p_throws"].mode().empty else "R"
 
        pitcher_profiles[pitcher_id] = PitcherProfile(
            pitcher_id=pitcher_id,
            throws=throws,
            pa_count=pa_count,
            avg=hits / at_bats,
            obp=(hits + group["is_BB"].sum() + group["is_HBP"].sum()) / pa_count,
            slg=group["total_bases"].sum() / at_bats,
            iso=(group["total_bases"].sum() / at_bats) - (hits / at_bats),
            k_rate=group["is_K"].sum() / pa_count,
            bb_rate=group["is_BB"].sum() / pa_count,
            hr_rate=group["is_HR"].sum() / pa_count,
            is_new=False,
        )
 
    return batter_profiles, pitcher_profiles
 
 
def make_league_avg_batter(batter_id: int = -1, stand: str = "R") -> BatterProfile:
    """Bateador 'promedio de liga' para rookies."""
    return BatterProfile(
        batter_id=batter_id, stand=stand, pa_count=0,
        avg=LEAGUE_AVG["avg"], obp=LEAGUE_AVG["obp"], slg=LEAGUE_AVG["slg"],
        iso=LEAGUE_AVG["iso"], k_rate=LEAGUE_AVG["k_rate"],
        bb_rate=LEAGUE_AVG["bb_rate"], hr_rate=LEAGUE_AVG["hr_rate"],
        is_rookie=True,
    )
 
 
def make_league_avg_pitcher(pitcher_id: int = -1, throws: str = "R") -> PitcherProfile:
    """Pitcher 'promedio de liga' para nuevos."""
    return PitcherProfile(
        pitcher_id=pitcher_id, throws=throws, pa_count=0,
        avg=LEAGUE_AVG["avg"], obp=LEAGUE_AVG["obp"], slg=LEAGUE_AVG["slg"],
        iso=LEAGUE_AVG["iso"], k_rate=LEAGUE_AVG["k_rate"],
        bb_rate=LEAGUE_AVG["bb_rate"], hr_rate=LEAGUE_AVG["hr_rate"],
        is_new=True,
    )
 
_BOOSTER_CACHE: dict[str, lgb.Booster] = {}

def load_booster(model_path) -> lgb.Booster:
      """Carga (y memoiza) el Booster por ruta."""
      key = str(model_path)
      if key not in _BOOSTER_CACHE:
          _BOOSTER_CACHE[key] = lgb.Booster(model_file=key)
      return _BOOSTER_CACHE[key]
class ModelSampler:
    
 
    def __init__(
        self,
        model_path: Path,
        feature_names: list[str],
        home_lineup: TeamLineup,
        away_lineup: TeamLineup,
        seed: Optional[int] = None,
    ):
        if isinstance(model_path, lgb.Booster):
              self.model = model_path
        else:
            self.model = load_booster(model_path)
        self.feature_names = feature_names
        self.home_lineup = home_lineup
        self.away_lineup = away_lineup
        self.rng = np.random.default_rng(seed)
 
    def _build_feature_vector(self, state: GameState) -> np.ndarray:
        
        # Identificar quién batea y quién pitcha
        if state.is_top:
            # Top inning: batea el visitante, pitcha el local
            batter = self.away_lineup.batter_at(state.away_batter_idx)
            pitcher = self.home_lineup.pitcher_for_inning(state.inning)
        else:
            # Bottom inning: batea el local, pitcha el visitante
            batter = self.home_lineup.batter_at(state.home_batter_idx)
            pitcher = self.away_lineup.pitcher_for_inning(state.inning)
 

        # Bases state: bit 0=1B, bit 1=2B, bit 2=3B
        on1b, on2b, on3b = state.bases
        bases_state = int(on1b) + int(on2b) * 2 + int(on3b) * 4
 
        # Score diff (desde la perspectiva del bateador)
        if state.is_top:
            # Bateador = away
            score_diff = state.away_score - state.home_score
        else:
            score_diff = state.home_score - state.away_score
 
        # Same-handed matchup
        same_handed = int(
            (batter.stand == "R" and pitcher.throws == "R") or
            (batter.stand == "L" and pitcher.throws == "L")
        )
 
        # --- Diccionario de todas las features ---
        # ¡El nombre de cada feature debe matchear feature_names.csv!
        features = {
            # Manos
            "p_throws_R":     int(pitcher.throws == "R"),
            "stand_R":        int(batter.stand == "R"),
            "stand_S":        int(batter.stand == "S"),
            "same_handed":    same_handed,
            # Game state
            "inning":         state.inning,
            "is_top":         int(state.is_top),
            "outs_when_up":   state.outs,
            "bases_state":    bases_state,
            "score_diff":     score_diff,
            # Bateador
            "b_pa_count":     batter.pa_count,
            "b_avg":          batter.avg,
            "b_obp":          batter.obp,
            "b_slg":          batter.slg,
            "b_iso":          batter.iso,
            "b_k_rate":       batter.k_rate,
            "b_bb_rate":      batter.bb_rate,
            "b_hr_rate":      batter.hr_rate,
            "b_is_rookie":    int(batter.is_rookie),
            # Pitcher
            "p_pa_count":     pitcher.pa_count,
            "p_avg":          pitcher.avg,
            "p_obp":          pitcher.obp,
            "p_slg":          pitcher.slg,
            "p_iso":          pitcher.iso,
            "p_k_rate":       pitcher.k_rate,
            "p_bb_rate":      pitcher.bb_rate,
            "p_hr_rate":      pitcher.hr_rate,
            "p_is_new":       int(pitcher.is_new),
        }
 
        # Construir vector en el orden correcto (el orden de feature_names)
        vec = np.array([features[name] for name in self.feature_names], dtype=np.float64)
        return vec.reshape(1, -1)  # 2D para LightGBM
 
    def __call__(self, state: GameState) -> Outcome:
        """
        Predice la distribución sobre outcomes y samplea uno.
        Esta es la interfaz que play_game llama en cada PA.
        """
        x = self._build_feature_vector(state)
        # predict() de LightGBM en multiclase devuelve (n_samples, n_classes)
        probs = self.model.predict(x)[0]  # vector de 8 probabilidades
 
        # Muestreo según la distribución predicha
        outcome_idx = self.rng.choice(len(probs), p=probs)
        return OUTCOME_FROM_INDEX[outcome_idx]
 
 

def build_lineup_from_ids(
    team_name: str,
    batter_ids: list[int],
    pitcher_id: int,
    batter_profiles: dict,
    pitcher_profiles: dict,
    bullpen_ids: Optional[list[int]] = None,
    reliever_entry_inning: int = 6,
) -> TeamLineup:
    """
    Construye un TeamLineup buscando los profiles por ID.
    Si algún ID no existe en los profiles (rookie), usa promedio de liga.

    `bullpen_ids` son los relevistas que entran a partir de
    `reliever_entry_inning` (default: inning 6).
    """
    if len(batter_ids) != 9:
        raise ValueError(f"Necesito 9 batter_ids, recibí {len(batter_ids)}")

    def _resolve_pitcher(pid: int) -> PitcherProfile:
        if pid in pitcher_profiles:
            return pitcher_profiles[pid]
        print(f"    pitcher_id {pid} no encontrado, usando promedio de liga")
        return make_league_avg_pitcher(pid)

    batters = []
    for bid in batter_ids:
        if bid in batter_profiles:
            batters.append(batter_profiles[bid])
        else:
            print(f"  batter_id {bid} no encontrado, usando promedio de liga")
            batters.append(make_league_avg_batter(bid))

    pitcher = _resolve_pitcher(pitcher_id)
    bullpen = [_resolve_pitcher(pid) for pid in (bullpen_ids or [])]

    return TeamLineup(
        team_name=team_name,
        batters=batters,
        pitcher=pitcher,
        bullpen=bullpen,
        reliever_entry_inning=reliever_entry_inning,
    )
BATTER_STAT_FIELDS = [
    "stand", "pa_count", "avg", "obp", "slg", "iso",
    "k_rate", "bb_rate", "hr_rate", "is_rookie",
]
PITCHER_STAT_FIELDS = [
    "throws", "pa_count", "avg", "obp", "slg", "iso",
    "k_rate", "bb_rate", "hr_rate", "is_new",
]

def _array_to_dict(arr, fields: list) -> dict:
    """Convierte un array posicional (o dict) en {campo: valor}."""
    if isinstance(arr, dict):
        return arr
    if len(arr) != len(fields):
        raise ValueError(
            f"Array de stats con longitud {len(arr)}, se esperaban "
            f"{len(fields)}: {fields}"
        )
    return dict(zip(fields, arr))

def batter_profile_from_array(arr, batter_id: int = -1) -> BatterProfile:
      """Construye un BatterProfile desde un array de stats (o dict)."""
      d = _array_to_dict(arr, BATTER_STAT_FIELDS)
      return BatterProfile(
          batter_id=batter_id,
          stand=str(d["stand"]),
          pa_count=float(d["pa_count"]),
          avg=float(d["avg"]),
          obp=float(d["obp"]),
          slg=float(d["slg"]),
          iso=float(d["iso"]),
          k_rate=float(d["k_rate"]),
          bb_rate=float(d["bb_rate"]),
          hr_rate=float(d["hr_rate"]),
          is_rookie=bool(d["is_rookie"]),
      )
      
def pitcher_profile_from_array(arr, pitcher_id: int = -1) -> PitcherProfile:
    """Construye un PitcherProfile desde un array de stats (o dict)."""
    d = _array_to_dict(arr, PITCHER_STAT_FIELDS)
    return PitcherProfile(
        pitcher_id=pitcher_id,
        throws=str(d["throws"]),
        pa_count=float(d["pa_count"]),
        avg=float(d["avg"]),
        obp=float(d["obp"]),
        slg=float(d["slg"]),
        iso=float(d["iso"]),
        k_rate=float(d["k_rate"]),
        bb_rate=float(d["bb_rate"]),
        hr_rate=float(d["hr_rate"]),
        is_new=bool(d["is_new"]),
    )
    
def build_lineup_from_stats(
      team_name: str,
      batter_arrays: list,
      pitcher_array,
      bullpen_arrays: Optional[list] = None,
      reliever_entry_inning: int = 6,
  ) -> TeamLineup:
      """
      Construye un TeamLineup directamente desde arrays de stats (sin IDs).
      `batter_arrays`: lista de 9 arrays. `pitcher_array`: array del abridor.
      `bullpen_arrays`: arrays de relevistas (opcional).
      """
      if len(batter_arrays) != 9:
          raise ValueError(f"Necesito 9 bateadores, recibí {len(batter_arrays)}")

      batters = [batter_profile_from_array(a) for a in batter_arrays]
      pitcher = pitcher_profile_from_array(pitcher_array)
      bullpen = [pitcher_profile_from_array(a) for a in (bullpen_arrays or [])]

      return TeamLineup(
          team_name=team_name,
          batters=batters,
          pitcher=pitcher,
          bullpen=bullpen,
          reliever_entry_inning=reliever_entry_inning,
      )


