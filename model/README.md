# SIMULATOR — ML-based MLB game simulator

Complete technical documentation for the project: data pipeline, model, simulator and Monte Carlo validation.

---

## Table of contents

1. [Project overview](#1-project-overview)
2. [Full pipeline flow](#2-full-pipeline-flow)
3. [Per-script documentation (.py): inputs, outputs and outcomes](#3-per-script-documentation)
4. [Schemas of all Parquet tables](#4-schemas-of-the-parquet-tables)
5. [Full flow of a single game simulation](#5-full-flow-of-a-single-game-simulation)
6. [Final results (project outcomes)](#6-final-results)

---

## 1. Project overview

The project builds an **MLB baseball game simulator** that works in three layers:

| Layer | What it does | Files |
|---|---|---|
| **Data** | Downloads pitch-by-pitch Statcast data (2024-2025), collapses it to *plate appearances* (PA) and builds batter/pitcher features | `download_stat.py`, `aggregate_to_pa.py`, `build_features.py`, `split_encode.py`, `download_lineups.py` |
| **Model** | Trains a multiclass LightGBM that predicts the outcome of each PA (8 classes: K, BB, HBP, 1B, 2B, 3B, HR, OUT) | `train_model.py` |
| **Simulation** | Baseball rules engine (`GameState`) + model sampler (`ModelSampler`) + Monte Carlo win probability over real games (`montecarlo.py`) | `gamestate.py`, `simulador.py`, `model_sampler.py`, `montecarlo.py`, `check_nobatter.py` |

**Core idea:** instead of directly predicting who wins a game, the model predicts the probability distribution of the outcome of **each at-bat** given the context (who is batting, who is pitching, inning, outs, runners, score). The simulator chains thousands of PAs sampled from the model to play complete games, and by repeating each game N times it obtains a **win probability** via Monte Carlo.

### The 8 PA outcome classes

| Class | Meaning | League frequency 2024 |
|---|---|---|
| `K` | Strikeout | 22.6% |
| `BB` | Walk (base on balls) | 8.2% |
| `HBP` | Hit by pitch | 1.1% |
| `1B` | Single | 14.8% |
| `2B` | Double | 4.3% |
| `3B` | Triple | 0.4% |
| `HR` | Home run | 3.0% |
| `OUT` | Out in play (groundout, flyout, etc.) | 45.6% |

---

## 2. Full pipeline flow

Execution order of the scripts and artifacts each one produces:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: DATA                                                            │
│                                                                          │
│  download_stat.py                                                        │
│  (pybaseball / Baseball Savant)                                          │
│        │                                                                 │
│        ├──► data/statcast_2024.parquet   (710,631 pitches × 118 cols)    │
│        └──► data/statcast_2025.parquet   (711,897 pitches × 118 cols)    │
│                       │                                                  │
│  aggregate_to_pa.py   ▼  (collapses pitches → plate appearances)         │
│        ├──► data/pa_2024.parquet         (182,120 PAs × 19 cols)         │
│        └──► data/pa_2025.parquet         (182,773 PAs × 19 cols)         │
│                       │                                                  │
│  build_features.py    ▼  (2024 player stats → features on 2025 PAs)      │
│        └──► data/pa_2025_with_features.parquet (182,773 × 37 cols)       │
│                       │                                                  │
│  split_encode.py      ▼  (encoding + temporal split)                     │
│        ├──► data/train.parquet           (122,956 PAs, up to Jul 31)     │
│        ├──► data/val.parquet             ( 31,811 PAs, August)           │
│        ├──► data/test.parquet            ( 28,006 PAs, September)         │
│        └──► data/feature_names.csv       (27 features)                   │
└──────────────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────┐
│ PHASE 2: MODEL                                                           │
│                                                                          │
│  train_model.py  (multiclass LightGBM, 8 classes)                        │
│        ├──► models/pa_model.txt              (trained model)             │
│        ├──► models/predictions_test.parquet  (probabilities on test set) │
│        └──► models/feature_importance.csv    (gain per feature)          │
└──────────────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────┐
│ PHASE 3: SIMULATION AND VALIDATION                                       │
│                                                                          │
│  download_lineups.py  (MLB Stats API, real lineups from the test set)    │
│        ├──► data/boxscore_cache/*.json   (374 cached boxscores)          │
│        └──► data/lineups.parquet         (374 games × 8 cols)            │
│                                                                          │
│  gamestate.py     ──► rules engine (game state, base advancement)        │
│  simulador.py     ──► play_game() + league-average sampler (baseline)    │
│  model_sampler.py ──► sampler that uses the LightGBM model per PA         │
│  check_nobatter.py──► sanity check: player coverage in profiles          │
│                                                                          │
│  montecarlo.py  (200 sims/game × 374 real September games)               │
│        └──► models/wp_predictions.parquet  (374 games × 7 cols)          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Per-script documentation

### 3.1 `download_stat.py` — Statcast download

**Purpose:** downloads every pitch from the 2024 and 2025 regular seasons from Baseball Savant using `pybaseball.statcast()` and saves them as Parquet (snappy compression). It is idempotent: if the parquet already exists, it is skipped.

| | |
|---|---|
| **Input** | Nothing local — downloads from the internet. Ranges: 2024 (`2024-03-28` → `2024-09-29`), 2025 (`2025-03-27` → `2025-09-28`) |
| **Output** | `data/statcast_2024.parquet`, `data/statcast_2025.parquet` |
| **Real outcome** | 710,631 pitches (2024) and 711,897 pitches (2025), 118 columns each |

**Sample run (console output):**

```
Descargando datos de Statcast (2024-2025)
Datos se guardarán en: /home/jose/AI_Class/SIMULADOR/data
============================================================
  Descargando temporada 2024 (2024-03-28 → 2024-09-29)
============================================================
Temporada 2024 bajada:
  Pitches: 710,631
  Columnas: 118
  Tiempo: 24.3 minutos
  Memoria: 1450.2 MB
  Guardado en: data/statcast_2024.parquet (95.1 MB)
...
Descarga completa.
  2024:   710,631 pitches en statcast_2024.parquet
  2025:   711,897 pitches en statcast_2025.parquet
```

---

### 3.2 `aggregate_to_pa.py` — Pitches → Plate Appearances

**Purpose:** collapses the ~710k pitches per season into ~182k *plate appearances*. It takes the **last pitch** of each at-bat (the one with a non-null `events`), maps the ~30 Statcast event types to the **8 classes** (`EVENT_MAPPING`), drops events that are not PAs (stolen bases, balks, pickoffs — `EVENTS_TO_DROP`) and converts `on_1b/on_2b/on_3b` from runner IDs to booleans.

Notable mapping decisions:
- `field_error` → `1B` (the batter reaches base)
- `catcher_interf` → `BB`
- `sac_fly`, `sac_bunt`, double plays → `OUT`

| | |
|---|---|
| **Input** | `data/statcast_2024.parquet`, `data/statcast_2025.parquet` |
| **Output** | `data/pa_2024.parquet` (182,120 rows), `data/pa_2025.parquet` (182,773 rows), 19 columns |
| **Real outcome** | Outcome distribution practically identical to the league (see table below) |

**Resulting distribution (script outcome):**

| Class | 2024 | 2025 | League benchmark |
|---|---|---|---|
| OUT | 45.64% | 45.78% | 46.2% |
| K | 22.58% | 22.22% | 22.6% |
| 1B | 14.80% | 14.83% | 14.1% |
| BB | 8.23% | 8.45% | 8.2% |
| 2B | 4.26% | 4.23% | 4.4% |
| HR | 2.99% | 3.09% | 2.9% |
| HBP | 1.11% | 1.05% | 1.2% |
| 3B | 0.38% | 0.34% | 0.4% |

**Input → output example (conceptual):**

```
INPUT (pitch-level, 5 rows = 1 PA):
  game_pk=776309, at_bat_number=12, pitch 1..5, events=[NaN,NaN,NaN,NaN,"strikeout"]

OUTPUT (PA-level, 1 row):
  game_pk=776309, at_bat_number=12, batter=660271, pitcher=543037,
  inning=3, inning_topbot="Top", outs_when_up=1, on_1b=True, on_2b=False,
  on_3b=False, bat_score=2, fld_score=1, events_original="strikeout",
  pa_outcome="K"
```

---

### 3.3 `build_features.py` — Feature engineering

**Purpose:** computes the aggregated **2024** statistics of each batter (`b_*`) and each pitcher (`p_*`) — AVG, OBP, SLG, ISO, K%, BB%, HR% — and joins them to each **2025** PA. This way the model knows "how good" each player is without information leakage (the stats come from the previous season).

Imputation rules:
- Batters with `< 100 PA` in 2024 and pitchers with `< 50 PA` → assigned the **league averages** (`LEAGUE_AVG`).
- Players who do not appear in 2024 (rookies / newcomers): flag `b_is_rookie` / `p_is_new` = True + league averages.

| | |
|---|---|
| **Input** | `data/pa_2024.parquet` (stats source), `data/pa_2025.parquet` (target) |
| **Output** | `data/pa_2025_with_features.parquet` (182,773 rows × 37 columns) |
| **Real outcome** | ~660 batters and ~850 unique pitchers with 2024 stats; ~10% of 2025 PAs involve rookies |

**Input → output example:**

```
INPUT (a 2025 PA):
  batter=660271, pitcher=543037, pa_outcome="HR", inning=4, ...

OUTPUT (same PA with features added):
  ... + b_pa_count=636, b_avg=0.310, b_obp=0.412, b_slg=0.645,
        b_iso=0.335, b_k_rate=0.162, b_bb_rate=0.125, b_hr_rate=0.085,
        b_is_rookie=False,
        p_pa_count=701, p_avg=0.251, p_obp=0.315, p_slg=0.410,
        p_iso=0.159, p_k_rate=0.219, p_bb_rate=0.078, p_hr_rate=0.031,
        p_is_new=False
```

---

### 3.4 `split_encode.py` — Encoding + temporal split

**Purpose:** converts the categorical columns to numeric ones and performs the **temporal split** (never random, to avoid leaking information from the future):

Derived encodings:
- `p_throws_R`, `stand_R`, `stand_S` — handedness as 0/1
- `same_handed` — same-handed matchup (R vs R or L vs L)
- `is_top` — top half of the inning
- `score_diff` = `bat_score - fld_score` (batter's perspective)
- `bases_state` — bitmask 0-7 (bit0=1B, bit1=2B, bit2=3B)
- `target` — outcome as an integer 0-7 following the order `["K","BB","HBP","1B","2B","3B","HR","OUT"]`

| | |
|---|---|
| **Input** | `data/pa_2025_with_features.parquet` |
| **Output** | `data/train.parquet`, `data/val.parquet`, `data/test.parquet`, `data/feature_names.csv` |
| **Real outcome** | Train: 122,956 PAs (67.3%, up to 2025-07-31) · Val: 31,811 PAs (17.4%, August) · Test: 28,006 PAs (15.3%, September). 27 final features |

**Input → output example:**

```
INPUT:   stand="L", p_throws="R", inning_topbot="Top", bat_score=3,
         fld_score=1, on_1b=True, on_2b=False, on_3b=True, pa_outcome="2B"

OUTPUT:  stand_R=0, stand_S=0, p_throws_R=1, same_handed=0, is_top=1,
         score_diff=+2, bases_state=5 (1B+3B), target=4
```

---

### 3.5 `train_model.py` — LightGBM model training

**Purpose:** trains a **multiclass LightGBM** (8 classes, `multi_logloss`) with early stopping on validation, compares it against two baselines and produces extensive diagnostics (confusion matrix, feature importance, synthetic elite-vs-bad scenarios).

Key hyperparameters: `learning_rate=0.05`, `num_leaves=63`, `min_data_in_leaf=100`, `lambda_l2=0.1`, up to 1000 rounds with early stopping of 50.

| | |
|---|---|
| **Input** | `data/train.parquet`, `data/val.parquet`, `data/test.parquet`, `data/feature_names.csv` |
| **Output** | `models/pa_model.txt`, `models/predictions_test.parquet`, `models/feature_importance.csv` |
| **Real outcome (test set)** | **log_loss = 1.4751**, **accuracy = 45.05%** · League-average baseline: log_loss = 1.4920 · The model improves ~1.1% over the natural baseline (the 8 classes of a PA are intrinsically very noisy) |

**Top features by gain (script outcome):**

| # | Feature | % gain | Cumulative |
|---|---|---|---|
| 1 | `b_k_rate` | 11.7% | 11.7% |
| 2 | `p_k_rate` | 8.0% | 19.7% |
| 3 | `b_bb_rate` | 7.1% | 26.8% |
| 4 | `p_bb_rate` | 5.9% | 32.6% |
| 5 | `p_pa_count` | 5.6% | 38.3% |
| 6 | `b_pa_count` | 5.0% | 43.3% |
| 7 | `b_hr_rate` | 5.0% | 48.2% |
| 8 | `b_avg` | 4.3% | 52.6% |
| 9 | `score_diff` | 4.3% | 56.9% |
| 10 | `p_hr_rate` | 4.3% | 61.1% |

The batter's and pitcher's K and BB rates dominate — exactly what sabermetrics expects.

**Input → output example (a single prediction):**

```
INPUT (27-feature vector):
  b_k_rate=0.12, b_iso=0.27, b_hr_rate=0.06, p_k_rate=0.32, bases_state=0, ...

OUTPUT (distribution over 8 classes):
  K: 18.4%  BB: 11.2%  HBP: 1.1%  1B: 13.9%  2B: 4.6%  3B: 0.3%  HR: 4.8%  OUT: 45.7%
```

---

### 3.6 `gamestate.py` — Baseball rules engine

**Purpose:** the `GameState` dataclass that represents the complete state of a game and knows how to **apply an outcome** by moving runners, adding runs, switching half-innings and detecting the end of the game. It has no I/O — it is the "physics" of the simulator.

State it keeps: `inning`, `is_top`, `outs`, `bases` (a tuple of 3 booleans), `home_score`, `away_score`, `home_batter_idx`, `away_batter_idx` (position in the batting order, modulo 9).

Advancement rules implemented in `apply_outcome()`:

| Outcome | Effect |
|---|---|
| `K` | +1 out |
| `OUT` | +1 out; **sac fly**: if there is a runner on 3B and <2 outs, scores with 30% probability |
| `BB` / `HBP` | Forced advancement only of forced runners; bases loaded → 1 run scores |
| `1B` | Runners on 3B and 2B score; runner on 1B reaches **3B with 30% probability** (extra base), otherwise 2B |
| `2B` | Runners on 3B and 2B score; runner on 1B → 3B |
| `3B` | All runners score |
| `HR` | All runners score + the batter |

End of game (`is_game_over()`):
- Walk-off: bottom of the 9th (or extras) with the home team ahead.
- Inning ≥ 10 in the top with an unequal score (the previous bottom ended without a tie).

**Input → output example:**

```
INPUT:   state = <Top 3 | 1 out | bases [X-X] | score H2-A1>,  outcome = "1B"

OUTPUT:  runs_scored = 1  (the runner on 3B scores)
         state = <Top 3 | 1 out | bases [XX-] or [X-X] | score H2-A2>
         (the runner on 1B went to 2B, or to 3B with 30% probability)
```

---

### 3.7 `simulador.py` — Game engine + league baseline

**Purpose:** defines `play_game(sampler)` — the loop that plays a complete game PA by PA until `is_game_over()` — and the `LeagueAverageSampler`, a "dumb" sampler that ignores the context and always samples the league's average frequencies. It serves as the **v1 baseline** to calibrate the rules engine before plugging in the model.

`play_game` accepts any `sampler: Callable[[GameState], Outcome]` (strategy pattern: the same engine works for the baseline and for the ML model), an optional `initial_state` (key for Monte Carlo from intermediate states) and a safety cap `max_pas=1000`.

| | |
|---|---|
| **Input** | None on disk; an in-memory sampler |
| **Output** | `GameResult` objects (no files) |
| **Expected outcome when run** | Over 10,000 games simulated with league frequencies: ~4.4 runs/team, ~8.2 hits/team, ~76 PAs/game, ~8-9% extras, ~50% home wins (the sampler is symmetric) — all in line with `MLB_BENCHMARKS` |

**Structure of `GameResult` (output of each game):**

```python
GameResult(
    home_score=5, away_score=3,
    innings_played=9, total_pas=74,
    home_hits=9, away_hits=6,
    home_strikeouts=7, away_strikeouts=10,
    went_to_extras=False,
)
# properties: .home_won → True, .is_tie → False
```

**Sample console output:**

```
  RESULTADOS (20 de 10000 juegos)
============================================================
   #    Score (H-A)       Ks (H-A)     Extras
------------------------------------------------------------
   1            5-3           7-10          —
   2            2-6            9-8          —
   3            4-4           8-11         Sí
   ...
```

---

### 3.8 `model_sampler.py` — ML-model-based sampler

**Purpose:** the heart of the model↔simulator integration. It defines:

- `BatterProfile` / `PitcherProfile` — dataclasses with the stats the model expects.
- `TeamLineup` — 9 batters + 1 pitcher (validates the length).
- `build_player_profiles(pa_2024)` — builds the profiles of **all** players from the 2024 PAs.
- `make_league_avg_batter/pitcher()` — league-average profiles for unknown players.
- `ModelSampler` — a callable class: given a `GameState`, it identifies who is batting/pitching, builds the 27-feature vector (in the same order as `feature_names.csv`), asks the LightGBM for the 8 probabilities and **samples an outcome** with `rng.choice(p=probs)`.
- `build_lineup_from_ids()` — assembles a `TeamLineup` from MLB IDs, with a fallback to league average.
- `run_diagnostic_tests()` — 3 sanity tests, each simulating 500 games.

| | |
|---|---|
| **Input** | `models/pa_model.txt`, `data/feature_names.csv`, `data/pa_2024.parquet` |
| **Output** | None on disk — diagnostic report to the console |
| **Expected outcome** | Test 1 (symmetric lineups): ~50% home wins, ~8.8 combined runs ✓ · Test 2 (swapped lineups): the advantage follows the lineup, not the home/away side ✓ · Test 3 (elite vs bad): >2-run difference and >70% win pct for the elite team ✓ |

**Sampler input → output example (a single PA):**

```
INPUT:    GameState(<Bot 7 | 2 outs | bases [X--] | score H3-A4>)
          → home_lineup.batters[4] is batting, away_lineup.pitcher is pitching

VECTOR:   [p_throws_R=1, stand_R=0, ..., inning=7, is_top=0, outs_when_up=2,
           bases_state=1, score_diff=-1, b_avg=0.287, ..., p_k_rate=0.244, ...]

MODEL:    probs = [0.21, 0.09, 0.01, 0.14, 0.05, 0.004, 0.035, 0.461]

OUTPUT:   Sampled outcome, e.g. "1B"
```

---

### 3.9 `download_lineups.py` — Official lineups

**Purpose:** for each unique game in the test set (September 2025), downloads the **official boxscore** from the MLB Stats API (`statsapi.mlb.com`), with on-disk caching (`data/boxscore_cache/*.json`) and a rate limit of 1 req/sec. It extracts the starting batting order (9 IDs) and the starting pitcher of each side.

| | |
|---|---|
| **Input** | `data/test.parquet` (for the `game_pk`s), the internet (MLB Stats API) |
| **Output** | `data/lineups.parquet` (374 games), `data/boxscore_cache/` (374 JSONs) |
| **Real outcome** | 374 games successfully processed with a complete lineup |

**Sample output row:**

```python
{
  "game_pk": 776309,
  "game_date": "2025-09-03",
  "home_team": "Boston Red Sox",
  "away_team": "Cleveland Guardians",
  "home_batter_ids": [680776, 646240, 807799, ...],   # 9 IDs in batting order
  "home_pitcher_id": 671096,
  "away_batter_ids": [677587, 680757, ...],
  "away_pitcher_id": 663986,
}
```

---

### 3.10 `check_nobatter.py` — Coverage sanity check

**Purpose:** a diagnostic script that checks how many players from the September 2025 lineups **do not have** a profile in the 2024 data (rookies, minor-league call-ups). It measures the impact of league-average imputation.

| | |
|---|---|
| **Input** | `data/pa_2024.parquet`, `data/lineups.parquet` |
| **Output** | Console report only |

**Sample output:**

```
Batters únicos en lineups de septiembre: 412
Batters NO encontrados en profiles 2024: 58
Porcentaje faltante: 14.1%

Pitchers únicos: 188
Pitchers no encontrados: 31
Porcentaje: 16.5%

Juegos con al menos 1 batter faltante: 204/374 (54.5%)
```

*(Illustrative order-of-magnitude figures; the exact percentage depends on the data.)*

---

### 3.11 `montecarlo.py` — Monte Carlo win probability

**Purpose:** the final validation of the complete system. For each of the **374 real games** of September 2025:

1. Builds the real lineups (`build_lineup_from_ids`).
2. Creates a `ModelSampler` with a unique seed per game (`SEED + game_pk`).
3. Simulates the game **200 times** from the initial state (`monte_carlo_wp`).
4. `wp_home = home_wins / 200`.
5. Compares against the real result (extracted from the last PA of `pa_2025_with_features.parquet`).

It evaluates with accuracy, **Brier score**, log loss, and compares them against two baselines: a 50/50 prediction and "the home team always wins". It includes calibration analysis by WP buckets.

| | |
|---|---|
| **Input** | `models/pa_model.txt`, `data/feature_names.csv`, `data/pa_2024.parquet`, `data/lineups.parquet`, `data/pa_2025_with_features.parquet` |
| **Output** | `models/wp_predictions.parquet` (374 rows) |
| **Real outcome** | **Accuracy = 51.1%** · **Brier = 0.2513** · **Log loss = 0.6959** · real % home wins = 53.5%. Context: Vegas reaches 55-58%, the theoretical ceiling of baseball is ~63% — with only previous-season stats and 200 sims/game, ~51% is a reasonable starting point |

**Sample output row:**

```python
{
  "game_pk": 776309,
  "home_team": "Boston Red Sox",
  "away_team": "Cleveland Guardians",
  "wp_home": 0.615,        # 123 home wins in 200 sims
  "home_won": 1,           # real result
  "final_score": "5-2",
  "valid_sims": 200,
}
```

---

## 4. Schemas of the Parquet tables

Structure only (column name and type), no records.

### 4.1 `data/statcast_2024.parquet` / `data/statcast_2025.parquet`

**Granularity:** 1 row = 1 pitch. **Rows:** 710,631 (2024) / 711,897 (2025). **118 columns** (raw Baseball Savant schema). The columns the pipeline actually uses are marked with ★:

| Column | Type | Description |
|---|---|---|
| `pitch_type` | string | Pitch type (FF, SL, CH...) |
| `game_date` ★ | timestamp[ns] | Game date |
| `release_speed` | double | Release speed (mph) |
| `release_pos_x` / `release_pos_z` | double | Release point |
| `player_name` | string | Pitcher name |
| `batter` ★ / `pitcher` ★ | int64 | MLBAM IDs |
| `events` ★ | string | Event that ends the PA (only on the last pitch) |
| `description` | string | Pitch result (ball, called_strike...) |
| `zone` | int64 | Strike zone (1-14) |
| `des` | string | Narrative description |
| `game_type` | string | R = regular season |
| `stand` ★ / `p_throws` ★ | string | Batter / pitcher handedness (L/R/S) |
| `home_team` ★ / `away_team` ★ | string | Teams |
| `type` | string | B/S/X |
| `hit_location` | int64 | Fielder position |
| `bb_type` | string | Batted-ball type (ground_ball, fly_ball...) |
| `balls` / `strikes` | int64 | Count |
| `game_year` | int64 | Year |
| `pfx_x` / `pfx_z` | double | Pitch movement |
| `plate_x` / `plate_z` | double | Location over the plate |
| `on_1b` ★ / `on_2b` ★ / `on_3b` ★ | int64 | Runner ID on base (NaN if empty) |
| `outs_when_up` ★ | int64 | Outs at the start of the PA |
| `inning` ★ / `inning_topbot` ★ | int64 / string | Inning and half (Top/Bot) |
| `hc_x` / `hc_y` | double | Batted-ball coordinates |
| `vx0..az` | double | Trajectory physics (6 cols) |
| `sz_top` / `sz_bot` | double | Vertical strike zone |
| `hit_distance_sc` | int64 | Batted-ball distance |
| `launch_speed` / `launch_angle` | double / int64 | Exit velocity / angle |
| `effective_speed` | double | Perceived velocity |
| `release_spin_rate` / `release_extension` | int64 / double | Spin and extension |
| `game_pk` ★ | int64 | Unique game ID |
| `fielder_2..fielder_9` | int64 | Fielder IDs (8 cols) |
| `release_pos_y` | double | Release (depth) |
| `estimated_ba/woba/slg_using_speedangle` | double | Expected metrics (3 cols) |
| `woba_value` / `woba_denom` / `babip_value` / `iso_value` | double / int64 | Sabermetric values |
| `launch_speed_angle` | int64 | Contact category |
| `at_bat_number` ★ / `pitch_number` | int64 | PA number in the game / pitch in the PA |
| `pitch_name` | string | Human-readable pitch name |
| `home_score` / `away_score` / `bat_score` ★ / `fld_score` ★ | int64 | Scores |
| `post_*_score` | int64 | Scores after the pitch (4 cols) |
| `if/of_fielding_alignment` | string | Defensive alignment |
| `spin_axis` | int64 | Spin axis |
| `delta_home_win_exp` / `delta_run_exp` / `delta_pitcher_run_exp` | double | Changes in expectancies |
| `bat_speed` / `swing_length` / `hyper_speed` | double | Swing metrics |
| `home_score_diff` / `bat_score_diff` | int64 | Differentials |
| `home_win_exp` / `bat_win_exp` | double | Win expectancy |
| `age_pit` / `age_bat` (+ `_legacy`) | int64 | Ages (4 cols) |
| `n_thruorder_pitcher` / `n_priorpa_thisgame_player_at_bat` | int64 | Times through the order |
| `pitcher/batter_days_since_prev_game`, `..._until_next_game` | int64 | Rest (4 cols) |
| `api_break_*` | double | Pitch break (3 cols) |
| `arm_angle`, `attack_angle`, `attack_direction`, `swing_path_tilt` | double | Biomechanics |
| `intercept_ball_minus_batter_pos_{x,y}_inches` | double | Contact point |
| `spin_dir`, `*_deprecated`, `umpire`, `sv_id`, `tfs_*` | int64 | Obsolete/empty columns |

### 4.2 `data/pa_2024.parquet` / `data/pa_2025.parquet`

**Granularity:** 1 row = 1 plate appearance. **Rows:** 182,120 / 182,773. **19 columns:**

| Column | Type | Description |
|---|---|---|
| `game_pk` | int64 | Unique game ID |
| `game_date` | timestamp[ns] | Date |
| `at_bat_number` | int64 | PA number within the game |
| `pitcher` | int64 | Pitcher MLBAM ID |
| `batter` | int64 | Batter MLBAM ID |
| `p_throws` | string | Pitcher handedness (L/R) |
| `stand` | string | Batter handedness (L/R/S) |
| `inning` | int64 | Inning (1-9+) |
| `inning_topbot` | string | "Top" / "Bot" |
| `outs_when_up` | int64 | Outs at the start of the PA (0-2) |
| `on_1b` / `on_2b` / `on_3b` | bool | Is there a runner on that base? |
| `bat_score` | int64 | Runs of the batting team |
| `fld_score` | int64 | Runs of the fielding team |
| `home_team` / `away_team` | string | Team abbreviation |
| `events_original` | string | Raw Statcast event |
| `pa_outcome` | string | One of the 8 classes (K/BB/HBP/1B/2B/3B/HR/OUT) |

### 4.3 `data/pa_2025_with_features.parquet`

**Granularity:** 1 row = 1 2025 PA with 2024 stats attached. **Rows:** 182,773. **37 columns** = the 19 from `pa_2025.parquet` **+ 18 features:**

| Column | Type | Description |
|---|---|---|
| `b_pa_count` | int64 | Batter's PAs in 2024 (0 if rookie) |
| `b_avg` / `b_obp` / `b_slg` / `b_iso` | double | 2024 batting average / OBP / Slugging / Isolated power |
| `b_k_rate` / `b_bb_rate` / `b_hr_rate` | double | K / BB / HR rates per PA in 2024 |
| `b_is_rookie` | bool | No 2024 data → stats imputed with league averages |
| `p_pa_count` | int64 | PAs faced by the pitcher in 2024 |
| `p_avg` / `p_obp` / `p_slg` / `p_iso` | double | Pitcher's stats *against* in 2024 |
| `p_k_rate` / `p_bb_rate` / `p_hr_rate` | double | Pitcher's rates against |
| `p_is_new` | bool | Pitcher without 2024 data |

### 4.4 `data/train.parquet` / `data/val.parquet` / `data/test.parquet`

**Granularity:** 1 row = 1 model-ready PA. **Rows:** 122,956 / 31,811 / 28,006. **33 columns** = 27 features + target + 5 identification columns:

| Column | Type | Group |
|---|---|---|
| `p_throws_R` | int64 | Feature — right-handed pitcher (0/1) |
| `stand_R` / `stand_S` | int64 | Feature — right-handed / switch batter |
| `same_handed` | int64 | Feature — same-handed matchup |
| `inning` | int64 | Feature — inning |
| `is_top` | int64 | Feature — top half (0/1) |
| `outs_when_up` | int64 | Feature — outs (0-2) |
| `bases_state` | int64 | Feature — base bitmask (0-7) |
| `score_diff` | int64 | Feature — bat_score − fld_score |
| `b_pa_count` … `b_hr_rate` | int64/double | Features — 8 batter stats |
| `b_is_rookie` | int64 | Feature — rookie flag (0/1) |
| `p_pa_count` … `p_hr_rate` | int64/double | Features — 8 pitcher stats |
| `p_is_new` | int64 | Feature — new-pitcher flag (0/1) |
| `target` | int64 | **Label** — outcome 0-7 (order K,BB,HBP,1B,2B,3B,HR,OUT) |
| `game_pk` | int64 | ID — traceability |
| `game_date` | timestamp[ns] | ID — for the temporal split |
| `pitcher` / `batter` | int64 | ID — players |
| `pa_outcome` | string | ID — human-readable label |

### 4.5 `data/lineups.parquet`

**Granularity:** 1 row = 1 test-set game. **Rows:** 374. **8 columns:**

| Column | Type | Description |
|---|---|---|
| `game_pk` | int64 | Game ID |
| `game_date` | string | Date |
| `home_team` / `away_team` | string | Full team name |
| `home_batter_ids` | list\<int64\> | 9 IDs in batting order (starters) |
| `home_pitcher_id` | int64 | Home starting pitcher |
| `away_batter_ids` | list\<int64\> | 9 away IDs |
| `away_pitcher_id` | int64 | Away starting pitcher |

### 4.6 `models/predictions_test.parquet`

**Granularity:** 1 row = 1 test-set PA with its 8 predicted probabilities. **Rows:** 28,006. **10 columns:**

| Column | Type | Description |
|---|---|---|
| `p_K` / `p_BB` / `p_HBP` / `p_1B` / `p_2B` / `p_3B` / `p_HR` / `p_OUT` | double | Predicted probability of each class (sum to 1) |
| `target` | int64 | Real class (0-7) |
| `pa_outcome` | string | Human-readable real class |

### 4.7 `models/wp_predictions.parquet`

**Granularity:** 1 row = 1 real game validated by Monte Carlo. **Rows:** 374. **7 columns:**

| Column | Type | Description |
|---|---|---|
| `game_pk` | int64 | Game ID |
| `home_team` / `away_team` | string | Teams |
| `wp_home` | double | Home win probability (home_wins / valid_sims) |
| `home_won` | int64 | Real result (1 = home team won) |
| `final_score` | string | Real score "H-A" |
| `valid_sims` | int64 | Valid simulations (typically 200) |

### Other artifacts (not parquet)

| File | Content |
|---|---|
| `data/feature_names.csv` | The 27 features in the exact order the model expects (no header) |
| `models/pa_model.txt` | Serialized LightGBM model (v4, multiclass, 8 classes, 27 features) |
| `models/feature_importance.csv` | `feature, gain, pct, cum_pct` per feature |
| `data/boxscore_cache/*.json` | 374 raw boxscores from the MLB Stats API (cache) |

---

## 5. Full flow of a single game simulation

### 5.1 Main loop diagram

```
                    ┌─────────────────────────────────────────┐
                    │  play_game(sampler)        [simulador.py]│
                    └─────────────────────────────────────────┘
                                      │
            state = GameState()  (Top 1, 0 outs, empty bases, 0-0)
                                      │
              ┌───────────────────────▼───────────────────────┐
              │              state.is_game_over()?             │◄────────┐
              └───────┬───────────────────────────┬───────────┘         │
                   No │                           │ Yes                 │
                      ▼                           ▼                     │
   ┌──────────────────────────────────┐   return GameResult(...)        │
   │ outcome = sampler(state)         │                                 │
   │                                  │                                 │
   │  [ModelSampler.__call__]         │                                 │
   │  1. is_top → AWAY bats,          │                                 │
   │     HOME pitches (and vice versa)│                                 │
   │  2. batter = lineup[batter_idx]  │                                 │
   │  3. 27-feature vector:           │                                 │
   │     handedness, inning, outs,    │                                 │
   │     bases_state, score_diff,     │                                 │
   │     b_* stats, p_* stats         │                                 │
   │  4. probs = lgbm.predict(x)      │  ← 8 probabilities              │
   │  5. outcome = rng.choice(p=probs)│  ← random sampling              │
   └──────────────┬───────────────────┘                                 │
                  ▼                                                     │
   ┌──────────────────────────────────┐                                 │
   │ state.apply_outcome(outcome)     │                                 │
   │            [gamestate.py]        │                                 │
   │  • moves runners per the rule    │                                 │
   │  • adds runs to the batting team │                                 │
   │  • advances the batting order(m9)│                                 │
   │  • if outs ≥ 3 → switch half-    │                                 │
   │    inning (clears bases and outs)│                                 │
   └──────────────┬───────────────────┘                                 │
                  │   total_pas += 1, accumulates hits/Ks               │
                  └─────────────────────────────────────────────────────┘
```

### 5.2 Narrated step by step

1. **Initial state.** `GameState()`: inning 1, top half, 0 outs, empty bases, 0-0, both lineups start with batter #1.

2. **Each PA (at-bat):**
   - The `ModelSampler` looks at the state: if it is the **top**, the away team bats against the home pitcher; if it is the **bottom**, the reverse.
   - It builds the 27-feature vector by combining *game state* (inning, outs, bases, run differential from the batter's perspective, handedness matchup) with the *2024 stats* of the batter and the pitcher at bat.
   - The LightGBM returns the distribution over the 8 classes and **one is sampled** at random according to those probabilities (not the argmax — the randomness is what generates the realistic variability of a game).

3. **Apply the outcome.** `GameState.apply_outcome()` executes the baseball rules: forced runners on BB/HBP, 1-2 base advances on hits, everyone scores on HR, probabilistic sac fly (30%) on outs with a runner on 3B, and extra advance 1B→3B (30%) on singles. It adds runs, advances to the next batter (modulo 9) and, on the third out, switches half-inning.

4. **End of game.** After each PA, `is_game_over()` is evaluated: at least 9 innings, walk-off if the home team is ahead in the bottom of the 9th+, and extra innings until the tie is broken. A safety cap (`max_pas=1000`) aborts impossibly long games.

5. **Result.** `play_game` returns a `GameResult` with the score, innings, total PAs, hits, strikeouts and whether it went to extras.

### 5.3 From a single game to win probability (Monte Carlo)

```
For each real September 2025 game (374 games):

  lineups.parquet ──► build_lineup_from_ids() ──► TeamLineup home/away
                                                   (rookies → league average)
  pa_model.txt    ──► ModelSampler(seed = 42 + game_pk)

  repeat 200 times:
      result = play_game(sampler, initial_state=GameState())
      home_wins += result.home_won

  wp_home = home_wins / 200          ──► models/wp_predictions.parquet
  compare vs real result            ──► accuracy, Brier, log loss, calibration
```

Each game is simulated 200 times with the same lineup but a different sampling seed, so that the fraction of simulated home wins converges to the win probability implied by the PA model.

---

## 6. Final results

### PA model (at-bat level, test = September 2025)

| Metric | Model | Uniform baseline | League-average baseline |
|---|---|---|---|
| Log loss | **1.4751** | 2.0794 | 1.4920 |
| Accuracy | **45.1%** | 12.5% | ~45.8% (always OUT) |

The model improves ~1.1% in log loss over the league baseline — modest in appearance, but expected: the outcome of an individual PA is intrinsically almost random; the value of the model is in correctly shifting the probabilities *per matchup* (e.g. raising `p_K` from 22% to 35% against a dominant pitcher), which is what the simulator aggregates over the ~76 PAs per game.

### Win probability (game level, 374 real games)

| Metric | MC Model | 50/50 baseline | "Home always wins" |
|---|---|---|---|
| Accuracy | **51.1%** | 53.5%* | 53.5% |
| Brier score | **0.2513** | 0.2500 | 0.2488 |
| Log loss | **0.6959** | 0.6931 | — |

\* the "majority" baseline coincides with the real % of home wins (53.5%).

**Honest reading of the outcome:** at the game level the system still does not beat the trivial baselines (Vegas: 55-58%, theoretical ceiling ~63%). The identifiable causes: player stats frozen at 2024 (no recent 2025 form), no bullpen (the starter pitches the whole game), ~200 sims/game (noise of ±3.5 pp in the WP), and rookies imputed to league average (see `check_nobatter.py`). The complete chain **data → model → simulator → Monte Carlo** is validated end to end and the diagnostic tests confirm that the simulator is symmetric, sensitive to lineup quality, and well calibrated in its totals (≈8.8 combined runs per game, ~8-9% extras, ~76 PAs/game).

### Execution order to reproduce everything

```bash
python download_stat.py      # ~1 hour (download from Baseball Savant)
python aggregate_to_pa.py    # seconds
python build_features.py     # seconds
python split_encode.py       # seconds
python train_model.py        # 1-2 minutes
python download_lineups.py   # ~10 min the first time (uses cache afterwards)
python check_nobatter.py     # optional, diagnostic
python model_sampler.py      # optional, simulator diagnostic tests
python simulador.py          # optional, league-average baseline
python montecarlo.py         # ~30-60 min (374 games × 200 sims)
```

**Dependencies:** `pandas`, `numpy`, `pyarrow`, `pybaseball`, `lightgbm`, `scikit-learn`, `requests`, `tqdm`.
