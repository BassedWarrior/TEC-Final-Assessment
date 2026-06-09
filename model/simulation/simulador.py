import random
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Optional
from GameState import GameState, Outcome

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
    def __init__(self, freqs: dict = None, seed: Optional[int] = None):
        self.freqs = freqs or LEAGUE_AVG_FREQUENCIES
        self.outcomes = list(self.freqs.keys())
        self.weights = list(self.freqs.values())
        self.rng = random.Random(seed)

    def __call__(self, state: GameState) -> Outcome:
        # state se ignora en v1; mañana el modelo lo usará
        return self.rng.choices(self.outcomes, weights=self.weights, k=1)[0]


@dataclass
class InningStats:
    """Línea de un inning (un número de inning) con el aporte de cada equipo.

    El equipo visitante (away) batea en el Top y el local (home) en el Bottom,
    así que un mismo `inning_number` agrega ambos medios-innings.
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
    home_score: int
    away_score: int
    innings_played: int
    total_pas: int
    home_hits: int
    away_hits: int
    home_strikeouts: int  # ← NUEVO
    away_strikeouts: int
    went_to_extras: bool
    # Desglose por inning (solo si play_game se llamó con track_innings=True).
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
    max_pas: int = 1000,  # safety: evita loops infinitos por bugs
    track_innings: bool = False,  # acumula el desglose por inning (más costoso)
) -> GameResult:

    state = initial_state.copy() if initial_state else GameState()
    total_pas = 0
    home_hits = 0
    away_hits = 0
    home_strikeouts = 0  # ← NUEVO
    away_strikeouts = 0
    last_pa_inning = 1

    # Acumuladores por inning: {inning_number: {home_runs, away_runs, ...}}.
    # Solo se llenan si track_innings; si no, el overhead es nulo.
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
        # Fue a extras si se jugó al menos un PA en el inning 10 o posterior
        home_strikeouts=home_strikeouts,  # ← NUEVO
        away_strikeouts=away_strikeouts,
        went_to_extras=last_pa_inning > 9,
        innings=innings,
    )


MLB_BENCHMARKS = {
    "runs_per_team_per_game": 4.39,  # media de carreras por equipo
    "runs_std": 3.10,  # desviación estándar
    "hits_per_team_per_game": 8.18,  # hits promedio por equipo
    "pas_per_game": 76.5,  # PAs totales del juego (ambos equipos)
    "pct_extras": 0.087,  # ~8.7% de juegos a extras
    "home_win_pct": 0.540,  # ventaja del local (sin contexto = sampler simétrico = ~50%)
}


def simulate_many(n_games: int = 10_000, seed: int = 42) -> dict:
    """
    Simula n_games juegos con el sampler de liga promedio y reporta estadísticas
    agregadas para comparar contra MLB real.
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
    Imprime una tabla con los resultados de los primeros `max_rows` juegos:
    score final y strikeouts por equipo.
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

    # Imprimimos los primeros 20 con detalle
    print_game_results(results, max_rows=20)

    # Calculamos los aggregates
    stats = simulate_many(n_games=10_000)
