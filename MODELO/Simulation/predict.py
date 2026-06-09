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
