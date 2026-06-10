import random
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Optional
from gamestate import GameState, Outcome

LEAGUE_AVG_FREQUENCIES = {
    Outcome.STRIKEOUT: 0.226,
    Outcome.WALK: 0.082,
    Outcome.HIT_BY_PITCH: 0.012,
    Outcome.SINGLE: 0.141,
    Outcome.DOUBLE: 0.044,
    Outcome.TRIPLE: 0.004,
    Outcome.HOME_RUN: 0.029,
    Outcome.OUT_IN_PLAY: 0.435,
    Outcome.DOUBLE_PLAY: 0.020,
    Outcome.SAC_FLY: 0.007,
}

_total = sum(LEAGUE_AVG_FREQUENCIES.values())
assert abs(_total - 1.0) < 0.001, f"Frecuencias deben sumar 1, suman {_total}"


class LeagueAverageSampler:
    """Outcome sampler that draws from fixed league-average frequencies."""

    def __init__(self, freqs: dict = None, seed: Optional[int] = None):
        self.freqs = freqs or LEAGUE_AVG_FREQUENCIES
        self.outcomes = list(self.freqs.keys())
        self.weights = list(self.freqs.values())
        self.rng = random.Random(seed)

    def __call__(self, state: GameState) -> Outcome:
        # state is ignored in v1; later the model will use it
        return self.rng.choices(self.outcomes, weights=self.weights, k=1)[0]


@dataclass
class InningStats:
    """Line for an inning (one inning number) with each team's contribution.

    The away team bats in the top half and the home team in the bottom half,
    so a single `inning_number` aggregates both half-innings.
    """

    inning_number: int
    home_strikeouts: int = 0
    away_strikeouts: int = 0
    home_hits: int = 0
    away_hits: int = 0
    home_runs: int = 0
    away_runs: int = 0
    home_hr: int = 0
    away_hr: int = 0


@dataclass
class GameResult:
    """Final result of a simulated game with per-team totals and optional inning breakdown."""

    home_score: int
    away_score: int
    innings_played: int
    total_pas: int
    home_hits: int
    away_hits: int
    home_strikeouts: int  # ← NEW
    away_strikeouts: int
    went_to_extras: bool
    # Per-inning breakdown (only if play_game was called with track_innings=True).
    innings: Optional[list] = None

    @property
    def home_won(self) -> bool:
        return self.home_score > self.away_score

    @property
    def is_tie(self) -> bool:
        return self.home_score == self.away_score


HIT_OUTCOMES = {Outcome.SINGLE, Outcome.DOUBLE, Outcome.TRIPLE, Outcome.HOME_RUN}


def play_game(
    sampler: Callable[[GameState], Outcome],
    initial_state: Optional[GameState] = None,
    max_pas: int = 1000,  # safety: avoids infinite loops caused by bugs
    track_innings: bool = False,  # accumulate the per-inning breakdown (more costly)
) -> GameResult:
    """Simulate a full game with `sampler` and return the GameResult.

    Args:
        sampler: callable mapping a GameState to a sampled Outcome.
        initial_state: optional starting GameState (copied); defaults to a fresh game.
        max_pas: safety cap on total plate appearances to guard against infinite loops.
        track_innings: if True, also accumulate a per-inning breakdown (more costly).

    Returns:
        GameResult with the final score and aggregate stats.
    """
    state = initial_state.copy() if initial_state else GameState()
    total_pas = 0
    home_hits = 0
    away_hits = 0
    home_strikeouts = 0  # ← NEW
    away_strikeouts = 0
    last_pa_inning = 1

    # Per-inning accumulators: {inning_number: {home_runs, away_runs, ...}}.
    # Only filled if track_innings; otherwise the overhead is zero.
    inning_acc = (
        defaultdict(
            lambda: {
                "home_strikeouts": 0,
                "away_strikeouts": 0,
                "home_hits": 0,
                "away_hits": 0,
                "home_runs": 0,
                "away_runs": 0,
                "home_hr": 0,
                "away_hr": 0,
            }
        )
        if track_innings
        else None
    )

    while not state.is_game_over():
        if total_pas >= max_pas:
            raise RuntimeError(
                f"Juego excedió {max_pas} PAs — probable bug en is_game_over o "
                f"reglas. Estado actual: {state}"
            )
        outcome = sampler(state)

        is_home_batting = not state.is_top
        inning = state.inning
        last_pa_inning = inning

        runs = state.apply_outcome(outcome)

        total_pas += 1

        if outcome in HIT_OUTCOMES:
            if is_home_batting:
                home_hits += 1
            else:
                away_hits += 1
        if outcome == Outcome.STRIKEOUT:
            if is_home_batting:
                home_strikeouts += 1
            else:
                away_strikeouts += 1

        if track_innings:
            side = "home" if is_home_batting else "away"
            s = inning_acc[inning]
            s[f"{side}_runs"] += runs
            if outcome in HIT_OUTCOMES:
                s[f"{side}_hits"] += 1
            if outcome == Outcome.HOME_RUN:
                s[f"{side}_hr"] += 1
            if outcome == Outcome.STRIKEOUT:
                s[f"{side}_strikeouts"] += 1

    innings = None
    if track_innings:
        innings = [
            InningStats(inning_number=n, **inning_acc[n]) for n in sorted(inning_acc)
        ]

    return GameResult(
        home_score=state.home_score,
        away_score=state.away_score,
        innings_played=last_pa_inning,
        total_pas=total_pas,
        home_hits=home_hits,
        away_hits=away_hits,
        # Went to extras if at least one PA was played in the 10th inning or later
        home_strikeouts=home_strikeouts,  # ← NEW
        away_strikeouts=away_strikeouts,
        went_to_extras=last_pa_inning > 9,
        innings=innings,
    )


MLB_BENCHMARKS = {
    "runs_per_team_per_game": 4.39,  # mean runs per team
    "runs_std": 3.10,  # standard deviation
    "hits_per_team_per_game": 8.18,  # average hits per team
    "pas_per_game": 76.5,  # total PAs in the game (both teams)
    "pct_extras": 0.087,  # ~8.7% of games go to extras
    "home_win_pct": 0.540,  # home-field advantage (no context = symmetric sampler = ~50%)
}


def simulate_many(n_games: int = 10_000, seed: int = 42) -> dict:
    """
    Simulate n_games games with the league-average sampler and report aggregate
    statistics to compare against real MLB.
    """
    sampler = LeagueAverageSampler(seed=seed)
    results = [play_game(sampler) for _ in range(n_games)]

    home_scores = [r.home_score for r in results]
    away_scores = [r.away_score for r in results]
    all_scores = home_scores + away_scores

    home_hits = [r.home_hits for r in results]
    away_hits = [r.away_hits for r in results]
    all_hits = home_hits + away_hits

    total_pas = [r.total_pas for r in results]
    extras_pct = sum(r.went_to_extras for r in results) / n_games
    home_win_pct = sum(r.home_won for r in results) / n_games
    tie_pct = sum(r.is_tie for r in results) / n_games

    return {
        "n_games": n_games,
        "runs_per_team_per_game": statistics.mean(all_scores),
        "runs_std": statistics.stdev(all_scores),
        "hits_per_team_per_game": statistics.mean(all_hits),
        "pas_per_game": statistics.mean(total_pas),
        "pct_extras": extras_pct,
        "home_win_pct": home_win_pct,
        "tie_pct": tie_pct,
        "max_runs_in_game": max(all_scores),
        "shutouts_pct": sum(1 for s in all_scores if s == 0) / len(all_scores),
    }


def print_game_results(results: list[GameResult], max_rows: int = 20) -> None:
    """
    Print a table with the results of the first `max_rows` games:
    final score and strikeouts per team.
    """
    print("\n" + "=" * 60)
    print(f"  RESULTADOS ({min(len(results), max_rows)} de {len(results)} juegos)")
    print("=" * 60)
    print(f"{'#':>4} {'Score (H-A)':>14} {'Ks (H-A)':>14} {'Extras':>10}")
    print("-" * 60)

    for i, r in enumerate(results[:max_rows], start=1):
        score = f"{r.home_score}-{r.away_score}"
        ks = f"{r.home_strikeouts}-{r.away_strikeouts}"
        extras = "Sí" if r.went_to_extras else "—"
        print(f"{i:>4} {score:>14} {ks:>14} {extras:>10}")

    print("=" * 60)


if __name__ == "__main__":
    print("Simulando con sampler de frecuencias promedio de MLB...")
    sampler = LeagueAverageSampler(seed=42)
    results = [play_game(sampler) for _ in range(10_000)]

    # Print the first 20 in detail
    print_game_results(results, max_rows=20)

    # Compute the aggregates
    stats = simulate_many(n_games=10_000)
