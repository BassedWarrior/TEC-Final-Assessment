from pathlib import Path
from typing import Optional

import pandas as pd

from GameState import GameState
from Simulador import play_game
from Model_sampler import (
    ModelSampler,
    build_lineup_from_stats,
    load_booster,
)

# Rutas relativas al archivo (no al cwd): funciona aunque el API invoque desde otro dir.
_BASE_DIR = Path(__file__).resolve().parent.parent  # .../MODELO
MODEL_PATH = _BASE_DIR / "models" / "pa_model.txt"
FEATURE_NAMES_PATH = _BASE_DIR / "data" / "feature_names.csv"

_FEATURE_NAMES: Optional[list] = None


def _feature_names() -> list:
    """Lee feature_names.csv una sola vez."""
    global _FEATURE_NAMES
    if _FEATURE_NAMES is None:
        _FEATURE_NAMES = pd.read_csv(FEATURE_NAMES_PATH, header=None)[0].tolist()
    return _FEATURE_NAMES


def _monte_carlo_wp(sampler: ModelSampler, n_sims: int) -> tuple:
    """Simula n_sims juegos completos desde el inicio y cuenta victorias del local."""
    home_wins = 0
    valid_sims = 0
    for _ in range(n_sims):
        try:
            result = play_game(sampler, initial_state=GameState())
            if result.home_won:
                home_wins += 1
            valid_sims += 1
        except RuntimeError:
            continue  # juego excedió max_pas (raro)
    wp = home_wins / valid_sims if valid_sims > 0 else 0.5
    return wp, home_wins, valid_sims


def win_probability_from_stats(
    home_batters: list,
    home_pitcher,
    away_batters: list,
    away_pitcher,
    home_bullpen: Optional[list] = None,
    away_bullpen: Optional[list] = None,
    reliever_entry_inning: int = 6,
    n_sims: int = 500,
    seed: Optional[int] = None,
    home_team: str = "HOME",
    away_team: str = "AWAY",
) -> dict:
    """
    Calcula la win probability del local simulando el juego n_sims veces.

    home_batters / away_batters: lista de 9 arrays de stats de bateador.
    home_pitcher / away_pitcher: array de stats del abridor.
    *_bullpen: listas opcionales de arrays de relevistas.
    """
    booster = load_booster(MODEL_PATH)        # cargado una sola vez (cacheado)
    feature_names = _feature_names()

    home_lineup = build_lineup_from_stats(
        team_name=home_team,
        batter_arrays=home_batters,
        pitcher_array=home_pitcher,
        bullpen_arrays=home_bullpen,
        reliever_entry_inning=reliever_entry_inning,
    )
    away_lineup = build_lineup_from_stats(
        team_name=away_team,
        batter_arrays=away_batters,
        pitcher_array=away_pitcher,
        bullpen_arrays=away_bullpen,
        reliever_entry_inning=reliever_entry_inning,
    )

    sampler = ModelSampler(
        model_path=booster,                   # Booster ya cargado
        feature_names=feature_names,
        home_lineup=home_lineup,
        away_lineup=away_lineup,
        seed=seed,
    )

    wp_home, home_wins, valid_sims = _monte_carlo_wp(sampler, n_sims)

    return {
        "wp_home": round(wp_home, 4),
        "wp_away": round(1.0 - wp_home, 4),
        "home_wins": home_wins,
        "n_sims": n_sims,
        "valid_sims": valid_sims,
    }


def simulate_match_from_stats(
    home_batters: list,
    home_pitcher,
    away_batters: list,
    away_pitcher,
    home_bullpen: Optional[list] = None,
    away_bullpen: Optional[list] = None,
    reliever_entry_inning: int = 6,
    n_sims: int = 500,
    seed: Optional[int] = None,
    home_team: str = "HOME",
    away_team: str = "AWAY",
    match_id: int = 1,
) -> dict:
    """
    Igual que win_probability_from_stats, pero además del win-prob devuelve el
    desglose inning-por-inning de cada simulación, listo para persistir en el
    modelo relacional Match / Simulation / Inning.

    Estructura devuelta (IDs enteros, claves foráneas resueltas):
        {
          "match":       {id, home_wp, away_wp, total_sims},
          "simulations": [{id, match_id}, ...],          # una por sim válida
          "innings":     [{id, simulation_id, inning_number,
                           home_strikeouts, away_strikeouts,
                           home_hits, away_hits, home_runs, away_runs,
                           home_hr, away_hr}, ...],
        }

    STKO = strikeouts (ponches).
    """
    booster = load_booster(MODEL_PATH)
    feature_names = _feature_names()

    home_lineup = build_lineup_from_stats(
        team_name=home_team,
        batter_arrays=home_batters,
        pitcher_array=home_pitcher,
        bullpen_arrays=home_bullpen,
        reliever_entry_inning=reliever_entry_inning,
    )
    away_lineup = build_lineup_from_stats(
        team_name=away_team,
        batter_arrays=away_batters,
        pitcher_array=away_pitcher,
        bullpen_arrays=away_bullpen,
        reliever_entry_inning=reliever_entry_inning,
    )

    sampler = ModelSampler(
        model_path=booster,
        feature_names=feature_names,
        home_lineup=home_lineup,
        away_lineup=away_lineup,
        seed=seed,
    )

    simulations = []
    innings = []
    home_wins = 0
    valid_sims = 0
    sim_id = 0
    inning_id = 0

    for _ in range(n_sims):
        try:
            result = play_game(
                sampler, initial_state=GameState(), track_innings=True
            )
        except RuntimeError:
            continue  # juego excedió max_pas (raro)

        valid_sims += 1
        sim_id += 1
        if result.home_won:
            home_wins += 1

        simulations.append({"id": sim_id, "match_id": match_id})

        for inn in result.innings:
            inning_id += 1
            innings.append({
                "id":              inning_id,
                "simulation_id":   sim_id,
                "inning_number":   inn.inning_number,
                "home_strikeouts": inn.home_strikeouts,
                "away_strikeouts": inn.away_strikeouts,
                "home_hits":       inn.home_hits,
                "away_hits":       inn.away_hits,
                "home_runs":       inn.home_runs,
                "away_runs":       inn.away_runs,
                "home_hr":         inn.home_hr,
                "away_hr":         inn.away_hr,
            })

    wp_home = home_wins / valid_sims if valid_sims > 0 else 0.5

    return {
        "match": {
            "id":         match_id,
            "home_wp":    round(wp_home, 4),
            "away_wp":    round(1.0 - wp_home, 4),
            "total_sims": valid_sims,
        },
        "simulations": simulations,
        "innings":     innings,
    }


def to_nested(out: dict) -> dict:
    """
    Convierte la salida plana (relacional) de simulate_match_from_stats al formato
    ANIDADO Match -> Simulations -> sim_N -> inning_M -> stats.

    Útil para consumirlo como JSON directo (app/frontend). Para BD usa la forma
    plana original (mapea 1:1 a las tablas Match/Simulation/Inning).
    """
    # innings agrupados por simulación
    innings_by_sim: dict = {}
    for inn in out["innings"]:
        innings_by_sim.setdefault(inn["simulation_id"], []).append(inn)

    simulations = {}
    for sim in out["simulations"]:
        sid = sim["id"]
        sim_innings = {}
        for inn in sorted(innings_by_sim.get(sid, []), key=lambda x: x["inning_number"]):
            sim_innings[f"inning_{inn['inning_number']}"] = {
                "Home_STKO": inn["home_strikeouts"],
                "Away_STKO": inn["away_strikeouts"],
                "Home_Hits": inn["home_hits"],
                "Away_Hits": inn["away_hits"],
                "Home_Runs": inn["home_runs"],
                "Away_Runs": inn["away_runs"],
                "Home_HR":   inn["home_hr"],
                "Away_HR":   inn["away_hr"],
            }
        simulations[f"sim_{sid}"] = sim_innings

    return {
        "Home_wp":     out["match"]["home_wp"],
        "Away_wp":     out["match"]["away_wp"],
        "Simulations": simulations,
    }


if __name__ == "__main__":
    # Demo: lineup élite (home) vs lineup débil (away).
    # Array: [mano, pa_count, avg, obp, slg, iso, k_rate, bb_rate, hr_rate, flag]
    elite_b = ["R", 600, 0.310, 0.420, 0.580, 0.270, 0.150, 0.130, 0.060, 0]
    weak_b  = ["R", 300, 0.220, 0.280, 0.330, 0.110, 0.280, 0.060, 0.015, 0]
    elite_p = ["R", 700, 0.210, 0.270, 0.330, 0.120, 0.300, 0.060, 0.020, 0]
    weak_p  = ["R", 600, 0.280, 0.350, 0.470, 0.190, 0.170, 0.090, 0.040, 0]

    out = win_probability_from_stats(
        home_batters=[elite_b] * 9, home_pitcher=elite_p,
        away_batters=[weak_b] * 9,  away_pitcher=weak_p,
        n_sims=300, seed=42,
    )
    print(out)  # wp_home esperado: alto (>0.7)
