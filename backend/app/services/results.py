"""
Result aggregation.

Turns the model API's flat per-simulation / per-inning output into the averages
we persist: for each team, the mean runs (score), hits, home runs and strikeouts
both per inning and for the whole game, plus each team's win probability.

Averaging convention:
    average = (sum of the metric over every simulation) / total_sims.
Simulations that never reached a given inning (walk-offs, games that ended
before extra innings) contribute 0 to that inning.

In the per-inning breakdown, RUNS are cumulative (a running scoreline: each
inning adds the previous innings' runs), so the last inning equals the
whole-game average. Hits/HR/strikeouts remain per-inning.
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


def aggregate_results(model_out: dict) -> dict:
    """
    Aggregate the flat model output into match-level and per-inning averages.

    Returns:
        {
          "home_wp", "away_wp", "total_sims",
          "whole_game": {avg_home_runs, avg_away_runs, ...},      # 8 keys
          "innings": [{inning_number, avg_home_runs, ...}, ...],  # one per inning
        }
    Keys in "whole_game" and each inning row match the Match / MatchInning
    column names so they can be splatted straight into the ORM models.
    """
    match = model_out["match"]
    total_sims = match.get("total_sims") or 0
    denom = total_sims if total_sims > 0 else 1

    game_sums: dict = defaultdict(float)
    inning_sums: dict = defaultdict(lambda: defaultdict(float))

    for inn in model_out["innings"]:
        n = inn["inning_number"]
        for col, src in _METRIC_COLUMNS.items():
            value = inn[src]
            game_sums[col] += value
            inning_sums[n][col] += value

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
        "home_wp": match["home_wp"],
        "away_wp": match["away_wp"],
        "total_sims": total_sims,
        "whole_game": whole_game,
        "innings": innings,
    }
