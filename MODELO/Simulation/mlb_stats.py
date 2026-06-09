"""
mlb_stats.py
------------
Cliente compartido de estadisticas OFICIALES de MLB (statsapi.mlb.com).

Es la unica fuente de stats de jugador para todo el proyecto:
  - Entrenamiento  (build_features.py): frames de stats por jugador.
  - Backend         (predict.py via el caller): arrays de stats por ID.

Ambos consumen las MISMAS definiciones desde aqui, de modo que el modelo se
entrena y se sirve con exactamente las mismas features (sin distribution shift).

Diseño:
  - Las stats salen de UN bulk request por grupo/temporada (hitting/pitching),
    que ya viene agregado por jugador (los traspasados vienen combinados).
  - La lateralidad (bateo/lanzamiento) sale de /people en lotes.
  - Todo se cachea en disco; tras el primer fetch el resto es instantaneo.

NO toma decisiones de leak: el caller elige la temporada. Para entrenar y para
el backend usamos la temporada ANTERIOR completa (ver SOURCE_SEASON en
build_features.py).
"""

import json
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
_BASE_DIR = Path(__file__).resolve().parent.parent          # .../MODELO
CACHE_DIR = _BASE_DIR / "data" / "mlb_stats_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

API_STATS = "https://statsapi.mlb.com/api/v1/stats"
API_PEOPLE = "https://statsapi.mlb.com/api/v1/people"
TIMEOUT_SECONDS = 30
RATE_LIMIT_SECONDS = 1.0
PEOPLE_BATCH = 100          # IDs por request a /people

# Umbrales: por debajo de esto el ratio es ruido -> regresa a liga promedio.
MIN_PA_BATTER = 100
MIN_PA_PITCHER = 50

LEAGUE_AVG = {
    "avg":     0.243, "obp":     0.312, "slg":     0.399, "iso":     0.156,
    "k_rate":  0.226, "bb_rate": 0.082, "hr_rate": 0.029,
}

# Orden de los arrays que consume build_lineup_from_stats / predict.py.
# DEBE coincidir con BATTER_STAT_FIELDS / PITCHER_STAT_FIELDS en Model_sampler.
BATTER_ARRAY_FIELDS = [
    "stand", "pa_count", "avg", "obp", "slg", "iso",
    "k_rate", "bb_rate", "hr_rate", "is_rookie",
]
PITCHER_ARRAY_FIELDS = [
    "throws", "pa_count", "avg", "obp", "slg", "iso",
    "k_rate", "bb_rate", "hr_rate", "is_new",
]

# Caches en memoria (por proceso)
_SEASON_CACHE: dict = {}        # (group, season) -> {id: metrics_dict}
_HAND_CACHE: dict = {}          # id -> {"bat": "R", "throw": "R"}


# ---------------------------------------------------------------------------
# Helpers de parseo
# ---------------------------------------------------------------------------
def _safe_float(value, default: float = 0.0) -> float:
    """avg/obp/slg vienen como string ('.322'); '.---' en 0-AB."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _metrics_from_stat(stat: dict, is_pitcher: bool) -> dict:
    """Mapea el objeto 'stat' de la API a las 7 metricas + pa_count."""
    pa = stat.get("battersFaced") if is_pitcher else stat.get("plateAppearances")
    pa = int(pa or 0)

    avg = _safe_float(stat.get("avg"), LEAGUE_AVG["avg"])
    obp = _safe_float(stat.get("obp"), LEAGUE_AVG["obp"])
    slg = _safe_float(stat.get("slg"), LEAGUE_AVG["slg"])

    denom = pa if pa > 0 else 1
    return {
        "pa_count": pa,
        "avg":      avg,
        "obp":      obp,
        "slg":      slg,
        "iso":      slg - avg,
        "k_rate":   int(stat.get("strikeOuts") or 0) / denom,
        "bb_rate":  int(stat.get("baseOnBalls") or 0) / denom,
        "hr_rate":  int(stat.get("homeRuns") or 0) / denom,
    }


# ---------------------------------------------------------------------------
# Fetch + cache: stats de temporada (bulk)
# ---------------------------------------------------------------------------
def _fetch_season_splits(group: str, season: int) -> list:
    """Baja (y cachea en disco) todos los jugadores de una temporada/grupo."""
    cache_path = CACHE_DIR / f"{group}_{season}.json"
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    resp = requests.get(
        API_STATS,
        params={
            "stats": "season", "season": season, "group": group,
            "playerPool": "All", "gameType": "R", "limit": 5000,
        },
        timeout=TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    splits = resp.json()["stats"][0]["splits"]

    with open(cache_path, "w") as f:
        json.dump(splits, f)
    time.sleep(RATE_LIMIT_SECONDS)
    return splits


def season_stats(season: int) -> dict:
    """
    {"batters": {id: metrics}, "pitchers": {id: metrics}} para una temporada.
    Memoizado por proceso.
    """
    key_b, key_p = ("hitting", season), ("pitching", season)
    if key_b not in _SEASON_CACHE:
        _SEASON_CACHE[key_b] = {
            s["player"]["id"]: _metrics_from_stat(s["stat"], is_pitcher=False)
            for s in _fetch_season_splits("hitting", season)
        }
    if key_p not in _SEASON_CACHE:
        _SEASON_CACHE[key_p] = {
            s["player"]["id"]: _metrics_from_stat(s["stat"], is_pitcher=True)
            for s in _fetch_season_splits("pitching", season)
        }
    return {"batters": _SEASON_CACHE[key_b], "pitchers": _SEASON_CACHE[key_p]}


# ---------------------------------------------------------------------------
# Frames para ENTRENAMIENTO (build_features.py)
# ---------------------------------------------------------------------------
_FRAME_COLS = ["pa_count", "avg", "obp", "slg", "iso", "k_rate", "bb_rate", "hr_rate"]


def _frame(metrics_by_id: dict) -> pd.DataFrame:
    if not metrics_by_id:
        return pd.DataFrame(columns=_FRAME_COLS)
    df = pd.DataFrame.from_dict(metrics_by_id, orient="index")
    return df[_FRAME_COLS]


def batter_frame(season: int) -> pd.DataFrame:
    """DataFrame indexado por MLBAM id del bateador (sin imputar threshold)."""
    return _frame(season_stats(season)["batters"])


def pitcher_frame(season: int) -> pd.DataFrame:
    """DataFrame indexado por MLBAM id del pitcher (sin imputar threshold)."""
    return _frame(season_stats(season)["pitchers"])


# ---------------------------------------------------------------------------
# Fetch + cache: lateralidad
# ---------------------------------------------------------------------------
def _handedness(ids: list) -> dict:
    """{id: {"bat": "R/L/S", "throw": "R/L"}} para los IDs dados, cacheado."""
    missing = [pid for pid in set(ids) if pid not in _HAND_CACHE]

    # Cargar lo que ya este en disco
    disk_path = CACHE_DIR / "handedness.json"
    if missing and disk_path.exists():
        with open(disk_path) as f:
            disk = json.load(f)
        for pid in list(missing):
            if str(pid) in disk:
                _HAND_CACHE[pid] = disk[str(pid)]
        missing = [pid for pid in missing if pid not in _HAND_CACHE]

    # Bajar lo que falte en lotes
    for i in range(0, len(missing), PEOPLE_BATCH):
        batch = missing[i:i + PEOPLE_BATCH]
        resp = requests.get(
            API_PEOPLE,
            params={"personIds": ",".join(map(str, batch))},
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        for p in resp.json().get("people", []):
            _HAND_CACHE[p["id"]] = {
                "bat":   p.get("batSide", {}).get("code", "R"),
                "throw": p.get("pitchHand", {}).get("code", "R"),
            }
        time.sleep(RATE_LIMIT_SECONDS)

    # Persistir
    if missing:
        merged = {}
        if disk_path.exists():
            with open(disk_path) as f:
                merged = json.load(f)
        merged.update({str(pid): _HAND_CACHE[pid] for pid in _HAND_CACHE})
        with open(disk_path, "w") as f:
            json.dump(merged, f)

    return {pid: _HAND_CACHE.get(pid, {"bat": "R", "throw": "R"}) for pid in ids}


# ---------------------------------------------------------------------------
# Arrays de stats para el BACKEND (predict.py via el caller)
# ---------------------------------------------------------------------------
def _impute_metrics(metrics: Optional[dict], min_pa: int) -> tuple:
    """
    Devuelve (metrics_imputadas, is_missing).
    Aplica el MISMO threshold que el entrenamiento: pa < min_pa -> liga promedio.
    """
    if metrics is None:
        # Jugador ausente (rookie / sin datos la temporada fuente)
        m = {"pa_count": 0, **{k: LEAGUE_AVG[k] for k in LEAGUE_AVG}}
        return m, True

    if metrics["pa_count"] < min_pa:
        # Presente pero muestra chica: stats a liga promedio, conserva pa_count real
        m = {"pa_count": metrics["pa_count"], **{k: LEAGUE_AVG[k] for k in LEAGUE_AVG}}
        return m, False

    return metrics, False


def batter_array(player_id: int, season: int, hand: Optional[str] = None) -> list:
    """Array de stats de bateador en el orden de BATTER_ARRAY_FIELDS."""
    stats = season_stats(season)["batters"]
    m, missing = _impute_metrics(stats.get(player_id), MIN_PA_BATTER)
    if hand is None:
        hand = _handedness([player_id])[player_id]["bat"]
    return [
        hand, float(m["pa_count"]), m["avg"], m["obp"], m["slg"], m["iso"],
        m["k_rate"], m["bb_rate"], m["hr_rate"], int(missing),
    ]


def pitcher_array(player_id: int, season: int, hand: Optional[str] = None) -> list:
    """Array de stats de pitcher en el orden de PITCHER_ARRAY_FIELDS."""
    stats = season_stats(season)["pitchers"]
    m, missing = _impute_metrics(stats.get(player_id), MIN_PA_PITCHER)
    if hand is None:
        hand = _handedness([player_id])[player_id]["throw"]
    return [
        hand, float(m["pa_count"]), m["avg"], m["obp"], m["slg"], m["iso"],
        m["k_rate"], m["bb_rate"], m["hr_rate"], int(missing),
    ]


def lineup_arrays(
    batter_ids: list,
    pitcher_id: int,
    season: int,
    bullpen_ids: Optional[list] = None,
) -> tuple:
    """
    IDs -> arrays de stats listos para predict.win_probability_from_stats.

    Returns (batter_arrays[9], pitcher_array, bullpen_arrays).
    Resuelve la lateralidad de todos los IDs en un solo lote.
    """
    if len(batter_ids) != 9:
        raise ValueError(f"Necesito 9 batter_ids, recibi {len(batter_ids)}")

    bullpen_ids = bullpen_ids or []
    all_ids = list(batter_ids) + [pitcher_id] + list(bullpen_ids)
    hands = _handedness(all_ids)

    batters = [batter_array(bid, season, hand=hands[bid]["bat"]) for bid in batter_ids]
    pitcher = pitcher_array(pitcher_id, season, hand=hands[pitcher_id]["throw"])
    bullpen = [pitcher_array(pid, season, hand=hands[pid]["throw"]) for pid in bullpen_ids]
    return batters, pitcher, bullpen


# ---------------------------------------------------------------------------
# CLI: pre-calienta la cache de una temporada
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    print(f"Bajando stats oficiales de MLB para {season}...")
    stats = season_stats(season)
    bf, pf = batter_frame(season), pitcher_frame(season)
    print(f"  Bateadores: {len(bf):>5,}  |  bajo {MIN_PA_BATTER} PA: "
          f"{(bf['pa_count'] < MIN_PA_BATTER).sum():,}")
    print(f"  Pitchers:   {len(pf):>5,}  |  bajo {MIN_PA_PITCHER} PA: "
          f"{(pf['pa_count'] < MIN_PA_PITCHER).sum():,}")
    print(f"\nCache en: {CACHE_DIR}")
    print("\nEjemplo (array de bateador, Aaron Judge 592450):")
    print(" ", batter_array(592450, season))
