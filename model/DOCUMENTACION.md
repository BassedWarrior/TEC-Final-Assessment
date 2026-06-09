# SIMULADOR — Simulador de partidos de MLB basado en Machine Learning

Documentación técnica completa del proyecto: pipeline de datos, modelo, simulador y validación Monte Carlo.

---

## Índice

1. [Resumen del proyecto](#1-resumen-del-proyecto)
2. [Flujo completo del pipeline](#2-flujo-completo-del-pipeline)
3. [Documentación por script (.py): entradas, salidas y outcomes](#3-documentación-por-script)
4. [Esquemas de todas las tablas Parquet](#4-esquemas-de-las-tablas-parquet)
5. [Flujo completo de la simulación de un partido](#5-flujo-completo-de-la-simulación-de-un-partido)
6. [Resultados finales (outcomes del proyecto)](#6-resultados-finales)

---

## 1. Resumen del proyecto

El proyecto construye un **simulador de partidos de béisbol (MLB)** que funciona en tres capas:

| Capa | Qué hace | Archivos |
|---|---|---|
| **Datos** | Descarga pitch-by-pitch de Statcast (2024-2025), lo colapsa a *plate appearances* (PA) y construye features de bateadores/pitchers | `Download_stat.py`, `aggregate_to_PA.py`, `build_features.py`, `split_encode.py`, `Download_lineups.py` |
| **Modelo** | Entrena un LightGBM multiclase que predice el resultado de cada PA (8 clases: K, BB, HBP, 1B, 2B, 3B, HR, OUT) | `train_model.py` |
| **Simulación** | Motor de reglas de béisbol (`GameState`) + sampler del modelo (`Model_sampler`) + Monte Carlo de win probability sobre juegos reales (`MonteCarlo.py`) | `GameState.py`, `Simulador.py`, `Model_sampler.py`, `MonteCarlo.py`, `check_nobatter.py` |

**Idea central:** en lugar de predecir directamente quién gana un partido, el modelo predice la distribución de probabilidad del resultado de **cada turno al bate** dado el contexto (quién batea, quién pitcha, inning, outs, corredores, marcador). El simulador encadena miles de PAs muestreados del modelo para jugar partidos completos, y repitiendo cada partido N veces se obtiene una **probabilidad de victoria (win probability)** por Monte Carlo.

### Las 8 clases de outcome de un PA

| Clase | Significado | Frecuencia liga 2024 |
|---|---|---|
| `K` | Strikeout | 22.6% |
| `BB` | Base por bolas (walk) | 8.2% |
| `HBP` | Golpeado por lanzamiento | 1.1% |
| `1B` | Sencillo | 14.8% |
| `2B` | Doble | 4.3% |
| `3B` | Triple | 0.4% |
| `HR` | Home run | 3.0% |
| `OUT` | Out en jugada (groundout, flyout, etc.) | 45.6% |

---

## 2. Flujo completo del pipeline

Orden de ejecución de los scripts y artefactos que produce cada uno:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ FASE 1: DATOS                                                            │
│                                                                          │
│  Download_stat.py                                                        │
│  (pybaseball / Baseball Savant)                                          │
│        │                                                                 │
│        ├──► data/statcast_2024.parquet   (710,631 pitches × 118 cols)    │
│        └──► data/statcast_2025.parquet   (711,897 pitches × 118 cols)    │
│                       │                                                  │
│  aggregate_to_PA.py   ▼  (colapsa pitches → plate appearances)           │
│        ├──► data/pa_2024.parquet         (182,120 PAs × 19 cols)         │
│        └──► data/pa_2025.parquet         (182,773 PAs × 19 cols)         │
│                       │                                                  │
│  build_features.py    ▼  (stats 2024 de jugadores → features en PAs 2025)│
│        └──► data/pa_2025_with_features.parquet (182,773 × 37 cols)       │
│                       │                                                  │
│  split_encode.py      ▼  (encoding + split temporal)                     │
│        ├──► data/train.parquet           (122,956 PAs, hasta 31-jul)     │
│        ├──► data/val.parquet             ( 31,811 PAs, agosto)           │
│        ├──► data/test.parquet            ( 28,006 PAs, septiembre)       │
│        └──► data/feature_names.csv       (27 features)                   │
└──────────────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────┐
│ FASE 2: MODELO                                                           │
│                                                                          │
│  train_model.py  (LightGBM multiclase, 8 clases)                         │
│        ├──► models/pa_model.txt              (modelo entrenado)          │
│        ├──► models/predictions_test.parquet  (probas en test set)        │
│        └──► models/feature_importance.csv    (ganancia por feature)      │
└──────────────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────┐
│ FASE 3: SIMULACIÓN Y VALIDACIÓN                                          │
│                                                                          │
│  Download_lineups.py  (MLB Stats API, lineups reales del test set)       │
│        ├──► data/boxscore_cache/*.json   (374 boxscores cacheados)       │
│        └──► data/lineups.parquet         (374 juegos × 8 cols)           │
│                                                                          │
│  GameState.py     ──► motor de reglas (estado del juego, avance de bases)│
│  Simulador.py     ──► play_game() + sampler de liga promedio (baseline)  │
│  Model_sampler.py ──► sampler que usa el modelo LightGBM por PA          │
│  check_nobatter.py──► sanity check: cobertura de jugadores en profiles   │
│                                                                          │
│  MonteCarlo.py  (200 sims/juego × 374 juegos reales de septiembre)       │
│        └──► models/wp_predictions.parquet  (374 juegos × 7 cols)         │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Documentación por script

### 3.1 `Download_stat.py` — Descarga de Statcast

**Propósito:** baja todos los pitches de las temporadas regulares 2024 y 2025 desde Baseball Savant usando `pybaseball.statcast()` y los guarda como Parquet (compresión snappy). Es idempotente: si el parquet ya existe, lo salta.

| | |
|---|---|
| **Entrada** | Nada local — descarga de internet. Rangos: 2024 (`2024-03-28` → `2024-09-29`), 2025 (`2025-03-27` → `2025-09-28`) |
| **Salida** | `data/statcast_2024.parquet`, `data/statcast_2025.parquet` |
| **Outcome real** | 710,631 pitches (2024) y 711,897 pitches (2025), 118 columnas cada uno |

**Ejemplo de ejecución (salida en consola):**

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

### 3.2 `aggregate_to_PA.py` — Pitches → Plate Appearances

**Propósito:** colapsa los ~710k pitches por temporada a ~182k *plate appearances*. Toma el **último pitch** de cada turno (el que tiene `events` no-nulo), mapea los ~30 tipos de evento de Statcast a las **8 clases** (`EVENT_MAPPING`), descarta eventos que no son PAs (robos de base, balks, pickoffs — `EVENTS_TO_DROP`) y convierte `on_1b/on_2b/on_3b` de IDs de corredor a booleanos.

Decisiones de mapeo notables:
- `field_error` → `1B` (el bateador llega a base)
- `catcher_interf` → `BB`
- `sac_fly`, `sac_bunt`, dobles plays → `OUT`

| | |
|---|---|
| **Entrada** | `data/statcast_2024.parquet`, `data/statcast_2025.parquet` |
| **Salida** | `data/pa_2024.parquet` (182,120 filas), `data/pa_2025.parquet` (182,773 filas), 19 columnas |
| **Outcome real** | Distribución de outcomes prácticamente idéntica a la liga (ver tabla abajo) |

**Distribución resultante (outcome del script):**

| Clase | 2024 | 2025 | Benchmark liga |
|---|---|---|---|
| OUT | 45.64% | 45.78% | 46.2% |
| K | 22.58% | 22.22% | 22.6% |
| 1B | 14.80% | 14.83% | 14.1% |
| BB | 8.23% | 8.45% | 8.2% |
| 2B | 4.26% | 4.23% | 4.4% |
| HR | 2.99% | 3.09% | 2.9% |
| HBP | 1.11% | 1.05% | 1.2% |
| 3B | 0.38% | 0.34% | 0.4% |

**Ejemplo entrada → salida (conceptual):**

```
ENTRADA (pitch-level, 5 filas = 1 PA):
  game_pk=776309, at_bat_number=12, pitch 1..5, events=[NaN,NaN,NaN,NaN,"strikeout"]

SALIDA (PA-level, 1 fila):
  game_pk=776309, at_bat_number=12, batter=660271, pitcher=543037,
  inning=3, inning_topbot="Top", outs_when_up=1, on_1b=True, on_2b=False,
  on_3b=False, bat_score=2, fld_score=1, events_original="strikeout",
  pa_outcome="K"
```

---

### 3.3 `build_features.py` — Feature engineering

**Propósito:** calcula las estadísticas agregadas de **2024** de cada bateador (`b_*`) y cada pitcher (`p_*`) — AVG, OBP, SLG, ISO, K%, BB%, HR% — y las une a cada PA de **2025**. Así el modelo conoce "qué tan bueno" es cada jugador sin fuga de información (las stats vienen de la temporada anterior).

Reglas de imputación:
- Bateadores con `< 100 PA` en 2024 y pitchers con `< 50 PA` → se les asignan los **promedios de liga** (`LEAGUE_AVG`).
- Jugadores que no aparecen en 2024 (rookies / nuevos): flag `b_is_rookie` / `p_is_new` = True + promedios de liga.

| | |
|---|---|
| **Entrada** | `data/pa_2024.parquet` (fuente de stats), `data/pa_2025.parquet` (target) |
| **Salida** | `data/pa_2025_with_features.parquet` (182,773 filas × 37 columnas) |
| **Outcome real** | ~660 bateadores y ~850 pitchers únicos con stats 2024; ~10% de PAs 2025 involucran rookies |

**Ejemplo entrada → salida:**

```
ENTRADA (un PA de 2025):
  batter=660271, pitcher=543037, pa_outcome="HR", inning=4, ...

SALIDA (mismo PA con features añadidas):
  ... + b_pa_count=636, b_avg=0.310, b_obp=0.412, b_slg=0.645,
        b_iso=0.335, b_k_rate=0.162, b_bb_rate=0.125, b_hr_rate=0.085,
        b_is_rookie=False,
        p_pa_count=701, p_avg=0.251, p_obp=0.315, p_slg=0.410,
        p_iso=0.159, p_k_rate=0.219, p_bb_rate=0.078, p_hr_rate=0.031,
        p_is_new=False
```

---

### 3.4 `split_encode.py` — Encoding + split temporal

**Propósito:** convierte las columnas categóricas a numéricas y hace el **split temporal** (nunca aleatorio, para evitar fuga de información del futuro):

Encodings derivados:
- `p_throws_R`, `stand_R`, `stand_S` — manos como 0/1
- `same_handed` — matchup misma mano (R vs R o L vs L)
- `is_top` — parte alta del inning
- `score_diff` = `bat_score - fld_score` (perspectiva del bateador)
- `bases_state` — bitmask 0-7 (bit0=1B, bit1=2B, bit2=3B)
- `target` — outcome como entero 0-7 según el orden `["K","BB","HBP","1B","2B","3B","HR","OUT"]`

| | |
|---|---|
| **Entrada** | `data/pa_2025_with_features.parquet` |
| **Salida** | `data/train.parquet`, `data/val.parquet`, `data/test.parquet`, `data/feature_names.csv` |
| **Outcome real** | Train: 122,956 PAs (67.3%, hasta 2025-07-31) · Val: 31,811 PAs (17.4%, agosto) · Test: 28,006 PAs (15.3%, septiembre). 27 features finales |

**Ejemplo entrada → salida:**

```
ENTRADA:  stand="L", p_throws="R", inning_topbot="Top", bat_score=3,
          fld_score=1, on_1b=True, on_2b=False, on_3b=True, pa_outcome="2B"

SALIDA:   stand_R=0, stand_S=0, p_throws_R=1, same_handed=0, is_top=1,
          score_diff=+2, bases_state=5 (1B+3B), target=4
```

---

### 3.5 `train_model.py` — Entrenamiento del modelo LightGBM

**Propósito:** entrena un **LightGBM multiclase** (8 clases, `multi_logloss`) con early stopping sobre validación, lo compara contra dos baselines y produce diagnósticos extensos (matriz de confusión, importancia de features, escenarios sintéticos elite-vs-malo).

Hiperparámetros clave: `learning_rate=0.05`, `num_leaves=63`, `min_data_in_leaf=100`, `lambda_l2=0.1`, hasta 1000 rondas con early stopping de 50.

| | |
|---|---|
| **Entrada** | `data/train.parquet`, `data/val.parquet`, `data/test.parquet`, `data/feature_names.csv` |
| **Salida** | `models/pa_model.txt`, `models/predictions_test.parquet`, `models/feature_importance.csv` |
| **Outcome real (test set)** | **log_loss = 1.4751**, **accuracy = 45.05%** · Baseline liga-promedio: log_loss = 1.4920 · El modelo mejora ~1.1% sobre el baseline natural (las 8 clases de un PA son intrínsecamente muy ruidosas) |

**Top features por ganancia (outcome del script):**

| # | Feature | % ganancia | Acumulado |
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

Las tasas de K y BB del bateador y pitcher dominan — exactamente lo que la sabermetría espera.

**Ejemplo entrada → salida (una predicción):**

```
ENTRADA (vector de 27 features):
  b_k_rate=0.12, b_iso=0.27, b_hr_rate=0.06, p_k_rate=0.32, bases_state=0, ...

SALIDA (distribución sobre 8 clases):
  K: 18.4%  BB: 11.2%  HBP: 1.1%  1B: 13.9%  2B: 4.6%  3B: 0.3%  HR: 4.8%  OUT: 45.7%
```

---

### 3.6 `GameState.py` — Motor de reglas del béisbol

**Propósito:** dataclass `GameState` que representa el estado completo de un partido y sabe **aplicar un outcome** moviendo corredores, sumando carreras, cambiando half-innings y detectando el fin del juego. No tiene I/O — es la "física" del simulador.

Estado que mantiene: `inning`, `is_top`, `outs`, `bases` (tupla de 3 booleanos), `home_score`, `away_score`, `home_batter_idx`, `away_batter_idx` (posición en el orden al bate, módulo 9).

Reglas de avance implementadas en `apply_outcome()`:

| Outcome | Efecto |
|---|---|
| `K` | +1 out |
| `OUT` | +1 out; **sac fly**: si hay corredor en 3B y <2 outs, anota con probabilidad 30% |
| `BB` / `HBP` | Avance forzado solo de corredores obligados; bases llenas → anota 1 |
| `1B` | Anotan 3B y 2B; corredor de 1B llega a **3B con probabilidad 30%** (base extra), si no a 2B |
| `2B` | Anotan 3B y 2B; corredor de 1B → 3B |
| `3B` | Anotan todos los corredores |
| `HR` | Anotan todos + el bateador |

Fin del juego (`is_game_over()`):
- Walk-off: bottom del 9° (o extras) con el local arriba.
- Inning ≥ 10 en el top con marcador desigual (terminó el bottom anterior sin empate).

**Ejemplo entrada → salida:**

```
ENTRADA:  state = <Top 3 | 1 out | bases [X-X] | score H2-A1>,  outcome = "1B"

SALIDA:   runs_scored = 1  (anota el de 3B)
          state = <Top 3 | 1 out | bases [XX-] o [X-X] | score H2-A2>
          (corredor de 1B fue a 2B, o a 3B con prob. 30%)
```

---

### 3.7 `Simulador.py` — Motor de partidos + baseline de liga

**Propósito:** define `play_game(sampler)` — el loop que juega un partido completo PA por PA hasta que `is_game_over()` — y el `LeagueAverageSampler`, un sampler "tonto" que ignora el contexto y muestrea siempre las frecuencias promedio de la liga. Sirve como **baseline v1** para calibrar el motor de reglas antes de conectar el modelo.

`play_game` acepta cualquier `sampler: Callable[[GameState], Outcome]` (patrón estrategia: el mismo motor sirve para el baseline y para el modelo ML), un `initial_state` opcional (clave para Monte Carlo desde estados intermedios) y un tope de seguridad `max_pas=1000`.

| | |
|---|---|
| **Entrada** | Ninguna en disco; un sampler en memoria |
| **Salida** | Objetos `GameResult` (sin archivos) |
| **Outcome esperado al correrlo** | Sobre 10,000 juegos simulados con frecuencias de liga: ~4.4 carreras/equipo, ~8.2 hits/equipo, ~76 PAs/juego, ~8-9% extras, ~50% home wins (el sampler es simétrico) — todo en línea con `MLB_BENCHMARKS` |

**Estructura de `GameResult` (salida de cada partido):**

```python
GameResult(
    home_score=5, away_score=3,
    innings_played=9, total_pas=74,
    home_hits=9, away_hits=6,
    home_strikeouts=7, away_strikeouts=10,
    went_to_extras=False,
)
# propiedades: .home_won → True, .is_tie → False
```

**Ejemplo de salida en consola:**

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

### 3.8 `Model_sampler.py` — Sampler basado en el modelo ML

**Propósito:** el corazón de la integración modelo↔simulador. Define:

- `BatterProfile` / `PitcherProfile` — dataclasses con las stats que el modelo espera.
- `TeamLineup` — 9 bateadores + 1 pitcher (valida la longitud).
- `build_player_profiles(pa_2024)` — construye los profiles de **todos** los jugadores desde los PAs de 2024.
- `make_league_avg_batter/pitcher()` — perfiles promedio de liga para jugadores desconocidos.
- `ModelSampler` — clase callable: dado un `GameState`, identifica quién batea/pitcha, construye el vector de 27 features (en el mismo orden de `feature_names.csv`), pide al LightGBM las 8 probabilidades y **muestrea un outcome** con `rng.choice(p=probs)`.
- `build_lineup_from_ids()` — arma un `TeamLineup` desde IDs de MLB, con fallback a promedio de liga.
- `run_diagnostic_tests()` — 3 tests de sanidad simulando 500 juegos cada uno.

| | |
|---|---|
| **Entrada** | `models/pa_model.txt`, `data/feature_names.csv`, `data/pa_2024.parquet` |
| **Salida** | Ninguna en disco — reporte de diagnósticos en consola |
| **Outcome esperado** | Test 1 (lineups simétricos): ~50% home wins, ~8.8 carreras combinadas ✓ · Test 2 (lineups invertidos): la ventaja sigue al lineup, no al lado home/away ✓ · Test 3 (elite vs malo): diferencia >2 carreras y >70% win pct para el equipo elite ✓ |

**Ejemplo entrada → salida del sampler (un PA):**

```
ENTRADA:  GameState(<Bot 7 | 2 outs | bases [X--] | score H3-A4>)
          → batea home_lineup.batters[4], pitcha away_lineup.pitcher

VECTOR:   [p_throws_R=1, stand_R=0, ..., inning=7, is_top=0, outs_when_up=2,
           bases_state=1, score_diff=-1, b_avg=0.287, ..., p_k_rate=0.244, ...]

MODELO:   probs = [0.21, 0.09, 0.01, 0.14, 0.05, 0.004, 0.035, 0.461]

SALIDA:   Outcome muestreado, p.ej. "1B"
```

---

### 3.9 `Download_lineups.py` — Lineups oficiales

**Propósito:** para cada juego único del test set (septiembre 2025), baja el **boxscore oficial** desde la MLB Stats API (`statsapi.mlb.com`), con caché en disco (`data/boxscore_cache/*.json`) y rate limit de 1 req/seg. Extrae el batting order titular (9 IDs) y el pitcher abridor de cada lado.

| | |
|---|---|
| **Entrada** | `data/test.parquet` (para los `game_pk`), internet (MLB Stats API) |
| **Salida** | `data/lineups.parquet` (374 juegos), `data/boxscore_cache/` (374 JSONs) |
| **Outcome real** | 374 juegos procesados exitosamente con lineup completo |

**Ejemplo de una fila de salida:**

```python
{
  "game_pk": 776309,
  "game_date": "2025-09-03",
  "home_team": "Boston Red Sox",
  "away_team": "Cleveland Guardians",
  "home_batter_ids": [680776, 646240, 807799, ...],   # 9 IDs en orden al bate
  "home_pitcher_id": 671096,
  "away_batter_ids": [677587, 680757, ...],
  "away_pitcher_id": 663986,
}
```

---

### 3.10 `check_nobatter.py` — Sanity check de cobertura

**Propósito:** script de diagnóstico que verifica cuántos jugadores de los lineups de septiembre 2025 **no tienen** profile en los datos de 2024 (rookies, llamados de ligas menores). Mide el impacto de la imputación con promedio de liga.

| | |
|---|---|
| **Entrada** | `data/pa_2024.parquet`, `data/lineups.parquet` |
| **Salida** | Solo reporte en consola |

**Ejemplo de salida:**

```
Batters únicos en lineups de septiembre: 412
Batters NO encontrados en profiles 2024: 58
Porcentaje faltante: 14.1%

Pitchers únicos: 188
Pitchers no encontrados: 31
Porcentaje: 16.5%

Juegos con al menos 1 batter faltante: 204/374 (54.5%)
```

*(Cifras ilustrativas del orden de magnitud; el porcentaje exacto depende de los datos.)*

---

### 3.11 `MonteCarlo.py` — Win probability por Monte Carlo

**Propósito:** la validación final del sistema completo. Para cada uno de los **374 juegos reales** de septiembre 2025:

1. Construye los lineups reales (`build_lineup_from_ids`).
2. Crea un `ModelSampler` con seed único por juego (`SEED + game_pk`).
3. Simula el partido **200 veces** desde el estado inicial (`monte_carlo_wp`).
4. `wp_home = home_wins / 200`.
5. Compara contra el resultado real (extraído del último PA de `pa_2025_with_features.parquet`).

Evalúa con accuracy, **Brier score**, log loss, y los compara contra dos baselines: predicción 50/50 y "siempre gana el local". Incluye análisis de calibración por buckets de WP.

| | |
|---|---|
| **Entrada** | `models/pa_model.txt`, `data/feature_names.csv`, `data/pa_2024.parquet`, `data/lineups.parquet`, `data/pa_2025_with_features.parquet` |
| **Salida** | `models/wp_predictions.parquet` (374 filas) |
| **Outcome real** | **Accuracy = 51.1%** · **Brier = 0.2513** · **Log loss = 0.6959** · % home wins real = 53.5%. Contexto: Vegas logra 55-58%, el techo teórico del béisbol es ~63% — con solo stats de la temporada anterior y 200 sims/juego, ~51% es un punto de partida razonable |

**Ejemplo de una fila de salida:**

```python
{
  "game_pk": 776309,
  "home_team": "Boston Red Sox",
  "away_team": "Cleveland Guardians",
  "wp_home": 0.615,        # 123 victorias home en 200 sims
  "home_won": 1,           # resultado real
  "final_score": "5-2",
  "valid_sims": 200,
}
```

---

## 4. Esquemas de las tablas Parquet

Solo estructura (nombre de columna y tipo), sin registros.

### 4.1 `data/statcast_2024.parquet` / `data/statcast_2025.parquet`

**Granularidad:** 1 fila = 1 pitch. **Filas:** 710,631 (2024) / 711,897 (2025). **118 columnas** (esquema crudo de Baseball Savant). Las columnas que el pipeline realmente usa están marcadas con ★:

| Columna | Tipo | Descripción |
|---|---|---|
| `pitch_type` | string | Tipo de lanzamiento (FF, SL, CH...) |
| `game_date` ★ | timestamp[ns] | Fecha del juego |
| `release_speed` | double | Velocidad de salida (mph) |
| `release_pos_x` / `release_pos_z` | double | Punto de liberación |
| `player_name` | string | Nombre del pitcher |
| `batter` ★ / `pitcher` ★ | int64 | IDs MLBAM |
| `events` ★ | string | Evento que termina el PA (solo en el último pitch) |
| `description` | string | Resultado del pitch (ball, called_strike...) |
| `zone` | int64 | Zona de strike (1-14) |
| `des` | string | Descripción narrativa |
| `game_type` | string | R = temporada regular |
| `stand` ★ / `p_throws` ★ | string | Mano del bateador / pitcher (L/R/S) |
| `home_team` ★ / `away_team` ★ | string | Equipos |
| `type` | string | B/S/X |
| `hit_location` | int64 | Posición del fildeador |
| `bb_type` | string | Tipo de batazo (ground_ball, fly_ball...) |
| `balls` / `strikes` | int64 | Conteo |
| `game_year` | int64 | Año |
| `pfx_x` / `pfx_z` | double | Movimiento del pitch |
| `plate_x` / `plate_z` | double | Ubicación sobre el plato |
| `on_1b` ★ / `on_2b` ★ / `on_3b` ★ | int64 | ID del corredor en base (NaN si vacía) |
| `outs_when_up` ★ | int64 | Outs al iniciar el PA |
| `inning` ★ / `inning_topbot` ★ | int64 / string | Inning y mitad (Top/Bot) |
| `hc_x` / `hc_y` | double | Coordenadas del batazo |
| `vx0..az` | double | Física de la trayectoria (6 cols) |
| `sz_top` / `sz_bot` | double | Zona de strike vertical |
| `hit_distance_sc` | int64 | Distancia del batazo |
| `launch_speed` / `launch_angle` | double / int64 | Velocidad / ángulo de salida |
| `effective_speed` | double | Velocidad percibida |
| `release_spin_rate` / `release_extension` | int64 / double | Spin y extensión |
| `game_pk` ★ | int64 | ID único del juego |
| `fielder_2..fielder_9` | int64 | IDs de los fildeadores (8 cols) |
| `release_pos_y` | double | Liberación (profundidad) |
| `estimated_ba/woba/slg_using_speedangle` | double | Métricas esperadas (3 cols) |
| `woba_value` / `woba_denom` / `babip_value` / `iso_value` | double / int64 | Valores sabermétricos |
| `launch_speed_angle` | int64 | Categoría de contacto |
| `at_bat_number` ★ / `pitch_number` | int64 | Número de PA en el juego / pitch en el PA |
| `pitch_name` | string | Nombre legible del pitch |
| `home_score` / `away_score` / `bat_score` ★ / `fld_score` ★ | int64 | Marcadores |
| `post_*_score` | int64 | Marcadores después del pitch (4 cols) |
| `if/of_fielding_alignment` | string | Alineación defensiva |
| `spin_axis` | int64 | Eje de rotación |
| `delta_home_win_exp` / `delta_run_exp` / `delta_pitcher_run_exp` | double | Cambios en expectativas |
| `bat_speed` / `swing_length` / `hyper_speed` | double | Métricas de swing |
| `home_score_diff` / `bat_score_diff` | int64 | Diferenciales |
| `home_win_exp` / `bat_win_exp` | double | Win expectancy |
| `age_pit` / `age_bat` (+ `_legacy`) | int64 | Edades (4 cols) |
| `n_thruorder_pitcher` / `n_priorpa_thisgame_player_at_bat` | int64 | Veces a través del orden |
| `pitcher/batter_days_since_prev_game`, `..._until_next_game` | int64 | Descanso (4 cols) |
| `api_break_*` | double | Quiebre del pitch (3 cols) |
| `arm_angle`, `attack_angle`, `attack_direction`, `swing_path_tilt` | double | Biomecánica |
| `intercept_ball_minus_batter_pos_{x,y}_inches` | double | Punto de contacto |
| `spin_dir`, `*_deprecated`, `umpire`, `sv_id`, `tfs_*` | int64 | Columnas obsoletas/vacías |

### 4.2 `data/pa_2024.parquet` / `data/pa_2025.parquet`

**Granularidad:** 1 fila = 1 plate appearance. **Filas:** 182,120 / 182,773. **19 columnas:**

| Columna | Tipo | Descripción |
|---|---|---|
| `game_pk` | int64 | ID único del juego |
| `game_date` | timestamp[ns] | Fecha |
| `at_bat_number` | int64 | Número de PA dentro del juego |
| `pitcher` | int64 | ID MLBAM del pitcher |
| `batter` | int64 | ID MLBAM del bateador |
| `p_throws` | string | Mano del pitcher (L/R) |
| `stand` | string | Mano del bateador (L/R/S) |
| `inning` | int64 | Inning (1-9+) |
| `inning_topbot` | string | "Top" / "Bot" |
| `outs_when_up` | int64 | Outs al iniciar el PA (0-2) |
| `on_1b` / `on_2b` / `on_3b` | bool | ¿Hay corredor en esa base? |
| `bat_score` | int64 | Carreras del equipo que batea |
| `fld_score` | int64 | Carreras del equipo que fildea |
| `home_team` / `away_team` | string | Abreviatura del equipo |
| `events_original` | string | Evento crudo de Statcast |
| `pa_outcome` | string | Una de las 8 clases (K/BB/HBP/1B/2B/3B/HR/OUT) |

### 4.3 `data/pa_2025_with_features.parquet`

**Granularidad:** 1 fila = 1 PA de 2025 con stats 2024 anexadas. **Filas:** 182,773. **37 columnas** = las 19 de `pa_2025.parquet` **+ 18 features:**

| Columna | Tipo | Descripción |
|---|---|---|
| `b_pa_count` | int64 | PAs del bateador en 2024 (0 si rookie) |
| `b_avg` / `b_obp` / `b_slg` / `b_iso` | double | Promedio / OBP / Slugging / Poder aislado 2024 |
| `b_k_rate` / `b_bb_rate` / `b_hr_rate` | double | Tasas de K / BB / HR por PA en 2024 |
| `b_is_rookie` | bool | Sin datos 2024 → stats imputadas con liga |
| `p_pa_count` | int64 | PAs enfrentados por el pitcher en 2024 |
| `p_avg` / `p_obp` / `p_slg` / `p_iso` | double | Stats *en contra* del pitcher en 2024 |
| `p_k_rate` / `p_bb_rate` / `p_hr_rate` | double | Tasas en contra del pitcher |
| `p_is_new` | bool | Pitcher sin datos 2024 |

### 4.4 `data/train.parquet` / `data/val.parquet` / `data/test.parquet`

**Granularidad:** 1 fila = 1 PA listo para el modelo. **Filas:** 122,956 / 31,811 / 28,006. **33 columnas** = 27 features + target + 5 columnas de identificación:

| Columna | Tipo | Grupo |
|---|---|---|
| `p_throws_R` | int64 | Feature — pitcher derecho (0/1) |
| `stand_R` / `stand_S` | int64 | Feature — bateador derecho / ambidiestro |
| `same_handed` | int64 | Feature — matchup misma mano |
| `inning` | int64 | Feature — inning |
| `is_top` | int64 | Feature — parte alta (0/1) |
| `outs_when_up` | int64 | Feature — outs (0-2) |
| `bases_state` | int64 | Feature — bitmask de bases (0-7) |
| `score_diff` | int64 | Feature — bat_score − fld_score |
| `b_pa_count` … `b_hr_rate` | int64/double | Features — 8 stats del bateador |
| `b_is_rookie` | int64 | Feature — flag rookie (0/1) |
| `p_pa_count` … `p_hr_rate` | int64/double | Features — 8 stats del pitcher |
| `p_is_new` | int64 | Feature — flag pitcher nuevo (0/1) |
| `target` | int64 | **Label** — outcome 0-7 (orden K,BB,HBP,1B,2B,3B,HR,OUT) |
| `game_pk` | int64 | ID — trazabilidad |
| `game_date` | timestamp[ns] | ID — para el split temporal |
| `pitcher` / `batter` | int64 | ID — jugadores |
| `pa_outcome` | string | ID — label legible |

### 4.5 `data/lineups.parquet`

**Granularidad:** 1 fila = 1 juego del test set. **Filas:** 374. **8 columnas:**

| Columna | Tipo | Descripción |
|---|---|---|
| `game_pk` | int64 | ID del juego |
| `game_date` | string | Fecha |
| `home_team` / `away_team` | string | Nombre completo del equipo |
| `home_batter_ids` | list\<int64\> | 9 IDs en orden al bate (titulares) |
| `home_pitcher_id` | int64 | Pitcher abridor local |
| `away_batter_ids` | list\<int64\> | 9 IDs visitantes |
| `away_pitcher_id` | int64 | Pitcher abridor visitante |

### 4.6 `models/predictions_test.parquet`

**Granularidad:** 1 fila = 1 PA del test set con sus 8 probabilidades predichas. **Filas:** 28,006. **10 columnas:**

| Columna | Tipo | Descripción |
|---|---|---|
| `p_K` / `p_BB` / `p_HBP` / `p_1B` / `p_2B` / `p_3B` / `p_HR` / `p_OUT` | double | Probabilidad predicha de cada clase (suman 1) |
| `target` | int64 | Clase real (0-7) |
| `pa_outcome` | string | Clase real legible |

### 4.7 `models/wp_predictions.parquet`

**Granularidad:** 1 fila = 1 juego real validado por Monte Carlo. **Filas:** 374. **7 columnas:**

| Columna | Tipo | Descripción |
|---|---|---|
| `game_pk` | int64 | ID del juego |
| `home_team` / `away_team` | string | Equipos |
| `wp_home` | double | Win probability del local (home_wins / valid_sims) |
| `home_won` | int64 | Resultado real (1 = ganó el local) |
| `final_score` | string | Marcador real "H-A" |
| `valid_sims` | int64 | Simulaciones válidas (típicamente 200) |

### Otros artefactos (no parquet)

| Archivo | Contenido |
|---|---|
| `data/feature_names.csv` | Las 27 features en el orden exacto que espera el modelo (sin header) |
| `models/pa_model.txt` | Modelo LightGBM serializado (v4, multiclase, 8 clases, 27 features) |
| `models/feature_importance.csv` | `feature, gain, pct, cum_pct` por feature |
| `data/boxscore_cache/*.json` | 374 boxscores crudos de la MLB Stats API (caché) |

---

## 5. Flujo completo de la simulación de un partido

### 5.1 Diagrama del loop principal

```
                    ┌─────────────────────────────────────────┐
                    │  play_game(sampler)        [Simulador.py]│
                    └─────────────────────────────────────────┘
                                      │
            state = GameState()  (Top 1, 0 outs, bases vacías, 0-0)
                                      │
              ┌───────────────────────▼───────────────────────┐
              │              ¿state.is_game_over()?            │◄────────┐
              └───────┬───────────────────────────┬───────────┘         │
                   No │                           │ Sí                  │
                      ▼                           ▼                     │
   ┌──────────────────────────────────┐   return GameResult(...)        │
   │ outcome = sampler(state)         │                                 │
   │                                  │                                 │
   │  [ModelSampler.__call__]         │                                 │
   │  1. is_top → batea AWAY,         │                                 │
   │     pitcha HOME (y viceversa)    │                                 │
   │  2. batter = lineup[batter_idx]  │                                 │
   │  3. vector de 27 features:       │                                 │
   │     manos, inning, outs,         │                                 │
   │     bases_state, score_diff,     │                                 │
   │     stats b_*, stats p_*         │                                 │
   │  4. probs = lgbm.predict(x)      │  ← 8 probabilidades             │
   │  5. outcome = rng.choice(p=probs)│  ← muestreo aleatorio           │
   └──────────────┬───────────────────┘                                 │
                  ▼                                                     │
   ┌──────────────────────────────────┐                                 │
   │ state.apply_outcome(outcome)     │                                 │
   │            [GameState.py]        │                                 │
   │  • mueve corredores según regla  │                                 │
   │  • suma carreras al que batea    │                                 │
   │  • avanza el orden al bate(mod 9)│                                 │
   │  • si outs ≥ 3 → cambia half-    │                                 │
   │    inning (limpia bases y outs)  │                                 │
   └──────────────┬───────────────────┘                                 │
                  │   total_pas += 1, acumula hits/Ks                   │
                  └─────────────────────────────────────────────────────┘
```

### 5.2 Paso a paso narrado

1. **Estado inicial.** `GameState()`: inning 1, parte alta, 0 outs, bases vacías, 0-0, ambos lineups empiezan por el bateador #1.

2. **Cada PA (turno al bate):**
   - El `ModelSampler` mira el estado: si es **top**, batea el visitante contra el pitcher local; si es **bottom**, al revés.
   - Construye el vector de 27 features combinando *game state* (inning, outs, bases, diferencia de carreras desde la perspectiva del bateador, matchup de manos) con las *stats 2024* del bateador y del pitcher en turno.
   - El LightGBM devuelve la distribución sobre las 8 clases y se **muestrea** una al azar según esas probabilidades (no se toma el argmax — la aleatoriedad es lo que genera la variabilidad realista de un partido).

3. **Aplicar el outcome.** `GameState.apply_outcome()` ejecuta las reglas del béisbol: corredores forzados en BB/HBP, avances de 1-2 bases en hits, todos anotan en HR, sac fly probabilístico (30%) en outs con corredor en 3B y avance extra 1B→3B (30%) en sencillos. Suma carreras, avanza al siguiente bateador (módulo 9) y, al tercer out, cambia de half-inning.

4. **Fin del juego.** Tras cada PA se evalúa `is_game_over()`: mínimo 9 innings, walk-off si el local va arriba en el bottom del 9°+, y extra innings hasta romper el empate. Un tope de seguridad (`max_pas=1000`) aborta juegos imposiblemente largos.

5. **Resultado.** `play_game` devuelve un `GameResult` con marcador, innings, PAs totales, hits, strikeouts y si fue a extras.

### 5.3 De un partido a la win probability (Monte Carlo)

```
Para cada juego real de septiembre 2025 (374 juegos):

  lineups.parquet ──► build_lineup_from_ids() ──► TeamLineup home/away
                                                   (rookies → liga promedio)
  pa_model.txt    ──► ModelSampler(seed = 42 + game_pk)

  repetir 200 veces:
      resultado = play_game(sampler, initial_state=GameState())
      home_wins += resultado.home_won

  wp_home = home_wins / 200          ──► models/wp_predictions.parquet
  comparar vs resultado real         ──► accuracy, Brier, log loss, calibración
```

Cada partido se simula 200 veces con el mismo lineup pero distinta semilla de muestreo, de modo que la fracción de victorias simuladas del local converge a la probabilidad de victoria implícita en el modelo de PAs.

---

## 6. Resultados finales

### Modelo de PA (nivel turno al bate, test = septiembre 2025)

| Métrica | Modelo | Baseline uniforme | Baseline liga-promedio |
|---|---|---|---|
| Log loss | **1.4751** | 2.0794 | 1.4920 |
| Accuracy | **45.1%** | 12.5% | ~45.8% (siempre OUT) |

El modelo mejora ~1.1% en log loss sobre el baseline de liga — modesto en apariencia, pero esperado: el resultado de un PA individual es intrínsecamente casi aleatorio; el valor del modelo está en mover correctamente las probabilidades *por matchup* (p.ej. sube `p_K` de 22% a 35% ante un pitcher dominante), que es lo que el simulador agrega a lo largo de ~76 PAs por juego.

### Win probability (nivel partido, 374 juegos reales)

| Métrica | Modelo MC | Baseline 50/50 | "Home siempre gana" |
|---|---|---|---|
| Accuracy | **51.1%** | 53.5%* | 53.5% |
| Brier score | **0.2513** | 0.2500 | 0.2488 |
| Log loss | **0.6959** | 0.6931 | — |

\* el baseline "mayoría" coincide con el % real de victorias locales (53.5%).

**Lectura honesta del outcome:** a nivel partido el sistema aún no supera a los baselines triviales (Vegas: 55-58%, techo teórico ~63%). Las causas identificables: stats de jugadores congeladas en 2024 (sin forma reciente de 2025), sin bullpen (el abridor pitcha el juego completo), ~200 sims/juego (ruido de ±3.5 pp en la WP), y rookies imputados a liga promedio (ver `check_nobatter.py`). La cadena completa **datos → modelo → simulador → Monte Carlo** queda validada de extremo a extremo y los tests diagnósticos confirman que el simulador es simétrico, sensible a la calidad de los lineups y bien calibrado en sus totales (≈8.8 carreras combinadas por juego, ~8-9% de extras, ~76 PAs/juego).

### Orden de ejecución para reproducir todo

```bash
python Download_stat.py      # ~1 hora (descarga de Baseball Savant)
python aggregate_to_PA.py    # segundos
python build_features.py     # segundos
python split_encode.py       # segundos
python train_model.py        # 1-2 minutos
python Download_lineups.py   # ~10 min la primera vez (luego usa caché)
python check_nobatter.py     # opcional, diagnóstico
python Model_sampler.py      # opcional, tests diagnósticos del simulador
python Simulador.py          # opcional, baseline de liga promedio
python MonteCarlo.py         # ~30-60 min (374 juegos × 200 sims)
```

**Dependencias:** `pandas`, `numpy`, `pyarrow`, `pybaseball`, `lightgbm`, `scikit-learn`, `requests`, `tqdm`.
