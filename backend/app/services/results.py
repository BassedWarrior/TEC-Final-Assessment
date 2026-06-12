"""
Result aggregation.

Turns the model API's **nested** per-simulation / per-inning output into the
averages we persist: for each team, the mean runs, hits, home runs and strikeouts
both per inning and for the whole game, plus each team's win probability.

Averaging convention:
    average = (sum of the metric over every simulation) / total_sims.
Simulations that never reached a given inning (walk-offs, games that ended
before extra innings) contribute 0 to that inning.

In the per-inning breakdown, RUNS are cumulative (a running scoreline: each
inning adds the previous innings' runs), so the last inning equals the
whole-game average. Hits/HR/strikeouts remain per-inning.

Input nested format (from `to_nested` in `predict.py`):
{
  "Home_wp": 0.65, "Away_wp": 0.35,
  "Simulations": {
    "sim_1": {"inning_1": {Home_Runs: ..., Away_Runs: ..., ...}, ...},
    ...
  }
}
"""

from collections import defaultdict

# DB column name (without the "avg_" prefix) -> key in the model's inning rows.
_METRIC_COLUMNS = {
    "home_runs": "home_runs",
    "away_runs": "away_runs",
    "home_hits": "home_hits",
    "away_hits": "away_hits",
    "home_hr": "home_hr",
    "away_hr": "away_hr",
    "home_strikeouts": "home_strikeouts",
    "away_strikeouts": "away_strikeouts",
}


def aggregate_results(nested_out: dict) -> dict:
    """
    Aggregate the nested model output into match-level and per-inning averages.

    Args:
        nested_out: JSON from model API (nested format with Simulations dict).

    Returns:
        {
          "home_wp": float,
          "away_wp": float,
          "total_sims": int,
          "whole_game": {
              "avg_home_runs": float,
              "avg_away_runs": float,
              "avg_home_hits": float,
              "avg_away_hits": float,
              "avg_home_hr": float,
              "avg_away_hr": float,
              "avg_home_strikeouts": float,
              "avg_away_strikeouts": float,
          },
          "innings": [
              {
                  "inning_number": int,
                  "avg_home_runs": float,   # cumulative
                  "avg_away_runs": float,   # cumulative
                  "avg_home_hits": float,
                  "avg_away_hits": float,
                  "avg_home_hr": float,
                  "avg_away_hr": float,
                  "avg_home_strikeouts": float,
                  "avg_away_strikeouts": float,
              },
              ...
          ]
        }
    Keys in "whole_game" and each inning row match the Match / MatchInning
    column names so they can be splatted straight into the ORM models.
    """
    home_wp = nested_out["Home_wp"]
    away_wp = nested_out["Away_wp"]
    simulations = nested_out["Simulations"]

    total_sims = len(simulations)
    denom = total_sims if total_sims > 0 else 1

    game_sums: dict = defaultdict(float)
    inning_sums: dict = defaultdict(lambda: defaultdict(float))

    for sim_key, innings_dict in simulations.items():
        for inning_key, stats in innings_dict.items():
            inning_num = int(inning_key.split("_")[1])

            mapping = {
                "home_runs": stats.get("Home_Runs", 0),
                "away_runs": stats.get("Away_Runs", 0),
                "home_hits": stats.get("Home_Hits", 0),
                "away_hits": stats.get("Away_Hits", 0),
                "home_hr": stats.get("Home_HR", 0),
                "away_hr": stats.get("Away_HR", 0),
                "home_strikeouts": stats.get("Home_STKO", 0),
                "away_strikeouts": stats.get("Away_STKO", 0),
            }

            for metric, value in mapping.items():
                game_sums[metric] += value
                inning_sums[inning_num][metric] += value

    whole_game = {f"avg_{col}": game_sums[col] / denom for col in _METRIC_COLUMNS}

    # Per-inning averages. Runs are made CUMULATIVE across innings (a running
    # score: inning 2 = inning 1 + inning 2, ...) so the frontend can plot the
    # scoreline progression directly; the last inning equals the whole-game
    # average. Hits/HR/strikeouts stay per-inning.
    innings = []
    cumulative_runs = {"avg_home_runs": 0.0, "avg_away_runs": 0.0}
    for n in sorted(inning_sums):
        row = {
            "inning_number": n,
            **{f"avg_{col}": inning_sums[n][col] / denom for col in _METRIC_COLUMNS},
        }
        for key in cumulative_runs:
            cumulative_runs[key] += row[key]
            row[key] = cumulative_runs[key]
        innings.append(row)

    return {
        "home_wp": home_wp,
        "away_wp": away_wp,
        "total_sims": total_sims,
        "whole_game": whole_game,
        "innings": innings,
    }
