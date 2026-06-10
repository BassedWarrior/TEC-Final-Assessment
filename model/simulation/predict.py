from pathlib import Path
from typing import Optional

import pandas as pd

from gamestate import GameState
from simulador import play_game
from model_sampler import (
    ModelSampler,
    build_lineup_from_stats,
    load_booster,
)

# Paths relative to the file (not the cwd): works even if the API invokes from another dir.
_BASE_DIR = Path(__file__).resolve().parent.parent  # .../model
MODEL_PATH = _BASE_DIR /"model_trainning"/"trained_models"/"pa_model.txt"
FEATURE_NAMES_PATH = _BASE_DIR / "data" / "feature_names.csv"

_FEATURE_NAMES: Optional[list] = None


def _feature_names() -> list:
    """Read feature_names.csv only once."""
    global _FEATURE_NAMES
    if _FEATURE_NAMES is None:
        _FEATURE_NAMES = pd.read_csv(FEATURE_NAMES_PATH, header=None)[0].tolist()
    return _FEATURE_NAMES


def _monte_carlo_wp(sampler: ModelSampler, n_sims: int) -> tuple:
    """Simulate n_sims full games from the start and count the home team's wins."""
    home_wins = 0
    valid_sims = 0
    for _ in range(n_sims):
        try:
            result = play_game(sampler, initial_state=GameState())
            if result.home_won:
                home_wins += 1
            valid_sims += 1
        except RuntimeError:
            continue  # game exceeded max_pas (rare)
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
    Compute the home team's win probability by simulating the game n_sims times.

    home_batters / away_batters: list of 9 batter stats arrays.
    home_pitcher / away_pitcher: starting pitcher stats array.
    *_bullpen: optional lists of reliever arrays.
    """
    booster = load_booster(MODEL_PATH)  # loaded only once (cached)
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
        model_path=booster,  # Booster already loaded
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
    Same as win_probability_from_stats, but in addition to the win prob it
    returns the inning-by-inning breakdown of each simulation, ready to persist
    in the relational Match / Simulation / Inning model.

    Returned structure (integer IDs, foreign keys resolved):
        {
          "match":       {id, home_wp, away_wp, total_sims},
          "simulations": [{id, match_id}, ...],          # one per valid sim
          "innings":     [{id, simulation_id, inning_number,
                           home_strikeouts, away_strikeouts,
                           home_hits, away_hits, home_runs, away_runs,
                           home_hr, away_hr}, ...],
        }

    STKO = strikeouts.
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
            result = play_game(sampler, initial_state=GameState(), track_innings=True)
        except RuntimeError:
            continue  # game exceeded max_pas (rare)

        valid_sims += 1
        sim_id += 1
        if result.home_won:
            home_wins += 1

        simulations.append({"id": sim_id, "match_id": match_id})

        for inn in result.innings:
            inning_id += 1
            innings.append(
                {
                    "id": inning_id,
                    "simulation_id": sim_id,
                    "inning_number": inn.inning_number,
                    "home_strikeouts": inn.home_strikeouts,
                    "away_strikeouts": inn.away_strikeouts,
                    "home_hits": inn.home_hits,
                    "away_hits": inn.away_hits,
                    "home_runs": inn.home_runs,
                    "away_runs": inn.away_runs,
                    "home_hr": inn.home_hr,
                    "away_hr": inn.away_hr,
                }
            )

    wp_home = home_wins / valid_sims if valid_sims > 0 else 0.5

    return {
        "match": {
            "id": match_id,
            "home_wp": round(wp_home, 4),
            "away_wp": round(1.0 - wp_home, 4),
            "total_sims": valid_sims,
        },
        "simulations": simulations,
        "innings": innings,
    }


def to_nested(out: dict) -> dict:
    """
    Convert the flat (relational) output of simulate_match_from_stats into the
    NESTED format Match -> Simulations -> sim_N -> inning_M -> stats.

    Useful for consuming it as direct JSON (app/frontend). For the DB use the
    original flat form (maps 1:1 to the Match/Simulation/Inning tables).
    """
    # innings grouped by simulation
    innings_by_sim: dict = {}
    for inn in out["innings"]:
        innings_by_sim.setdefault(inn["simulation_id"], []).append(inn)

    simulations = {}
    for sim in out["simulations"]:
        sid = sim["id"]
        sim_innings = {}
        for inn in sorted(
            innings_by_sim.get(sid, []), key=lambda x: x["inning_number"]
        ):
            sim_innings[f"inning_{inn['inning_number']}"] = {
                "Home_STKO": inn["home_strikeouts"],
                "Away_STKO": inn["away_strikeouts"],
                "Home_Hits": inn["home_hits"],
                "Away_Hits": inn["away_hits"],
                "Home_Runs": inn["home_runs"],
                "Away_Runs": inn["away_runs"],
                "Home_HR": inn["home_hr"],
                "Away_HR": inn["away_hr"],
            }
        simulations[f"sim_{sid}"] = sim_innings

    return {
        "Home_wp": out["match"]["home_wp"],
        "Away_wp": out["match"]["away_wp"],
        "Simulations": simulations,
    }


if __name__ == "__main__":
    # Demo: elite lineup (home) vs weak lineup (away).
    # Array: [stand, pa_count, avg, obp, slg, iso, k_rate, bb_rate, hr_rate, flag]
    elite_b = ["R", 600, 0.310, 0.420, 0.580, 0.270, 0.150, 0.130, 0.060, 0]
    weak_b = ["R", 300, 0.220, 0.280, 0.330, 0.110, 0.280, 0.060, 0.015, 0]
    elite_p = ["R", 700, 0.210, 0.270, 0.330, 0.120, 0.300, 0.060, 0.020, 0]
    weak_p = ["R", 600, 0.280, 0.350, 0.470, 0.190, 0.170, 0.090, 0.040, 0]

    out = win_probability_from_stats(
        home_batters=[elite_b] * 9,
        home_pitcher=elite_p,
        away_batters=[weak_b] * 9,
        away_pitcher=weak_p,
        n_sims=300,
        seed=42,
    )
    print(out)  # expected wp_home: high (>0.7)
