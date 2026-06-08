import os
# Paralelizamos por juego (multiprocessing); cada worker debe usar UN solo hilo.
# Si no, LightGBM lanza varios hilos OMP por proceso y, con N workers, sobre-
# suscribe los cores y colapsa el throughput. Debe ir antes de importar numpy/lgb.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import json
import multiprocessing as mp
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
from tqdm import tqdm

from GameState import GameState
from Simulador import play_game

import importlib.util
spec = importlib.util.spec_from_file_location("model_sampler", "Model_sampler.py")
model_sampler_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model_sampler_module)

ModelSampler              = model_sampler_module.ModelSampler
TeamLineup                = model_sampler_module.TeamLineup
build_player_profiles     = model_sampler_module.build_player_profiles
build_lineup_from_ids     = model_sampler_module.build_lineup_from_ids


DATA_DIR = Path("./data")
MODELS_DIR = Path("./models")
BOXSCORE_CACHE_DIR = DATA_DIR / "boxscore_cache"

N_SIMS_PER_GAME = 1000
N_GAMES_TO_VALIDATE = None
SEED = 42

# Inning en que entra el primer relevista (cambio de pitcher del abridor al bullpen).
RELIEVER_ENTRY_INNING = 6


def build_bullpen_map(cache_dir: Path = BOXSCORE_CACHE_DIR) -> dict:
    """
    Lee los boxscores cacheados y devuelve, por game_pk, los relevistas reales
    de cada equipo (los pitchers que aparecen DESPUÉS del abridor, en orden de
    aparición).

    Estructura: {game_pk: {"home": [id, ...], "away": [id, ...]}}
    """
    bullpens = {}
    if not cache_dir.exists():
        print(f"  ⚠️  No existe {cache_dir}; se simulará sin bullpen.")
        return bullpens

    for fpath in cache_dir.glob("*.json"):
        try:
            data = json.loads(fpath.read_text())
            teams = data["teams"]
            # pitchers[0] es el abridor (coincide con lineups.parquet); el resto, bullpen
            bullpens[int(fpath.stem)] = {
                "home": list(teams["home"]["pitchers"][1:]),
                "away": list(teams["away"]["pitchers"][1:]),
            }
        except (KeyError, ValueError, json.JSONDecodeError):
            continue  # boxscore incompleto o corrupto: ese juego va sin bullpen

    return bullpens


def load_artifacts():
    print("Cargando artefactos...")
    model_path = MODELS_DIR / "pa_model.txt"
    feature_names = pd.read_csv(
        DATA_DIR / "feature_names.csv", header=None
    )[0].tolist()


    print("  Construyendo profiles de jugadores desde 2024...")
    pa_2024 = pd.read_parquet(DATA_DIR / "pa_2024.parquet")
    batter_profiles, pitcher_profiles = build_player_profiles(pa_2024)
    print(f"    {len(batter_profiles):,} bateadores, {len(pitcher_profiles):,} pitchers")

    
    lineups = pd.read_parquet(DATA_DIR / "lineups.parquet")
    print(f"  {len(lineups):,} juegos con lineups disponibles")

    bullpen_map = build_bullpen_map()
    print(f"  {len(bullpen_map):,} juegos con bullpen (relevistas) desde boxscores")

    
    pa_2025 = pd.read_parquet(DATA_DIR / "pa_2025_with_features.parquet")

      
    last_pas = pa_2025.sort_values(
          ["game_pk", "at_bat_number"]
      ).groupby("game_pk").tail(1)

    last_pas = last_pas.copy()
    last_pas["final_home_score"] = np.where(
        last_pas["inning_topbot"] == "Top",
        last_pas["fld_score"],
        last_pas["bat_score"],
    )
    last_pas["final_away_score"] = np.where(
        last_pas["inning_topbot"] == "Top",
        last_pas["bat_score"],
        last_pas["fld_score"],
    )
    results = last_pas[["game_pk", "final_home_score", "final_away_score"]].copy()
    results["home_won"] = (results["final_home_score"] > results["final_away_score"]).astype(int)

    return model_path, feature_names, batter_profiles, pitcher_profiles, lineups, results, bullpen_map



def monte_carlo_wp(
    initial_state: GameState,
    sampler: ModelSampler,
    n_sims: int,
) -> tuple[float, int, int]:
    
    home_wins = 0
    valid_sims = 0
    for _ in range(n_sims):
        try:
            result = play_game(sampler, initial_state=initial_state.copy())
            if result.home_won:
                home_wins += 1
            valid_sims += 1
        except RuntimeError:
            # Juego excedió max_pas (raro pero puede pasar)
            continue

    wp = home_wins / valid_sims if valid_sims > 0 else 0.5
    return wp, home_wins, valid_sims



# --- Worker paralelo: cada juego es independiente; se reparten en los cores. ---
# Misma simulación que el loop serial, solo cambia que corre en paralelo y con
# 1 hilo por proceso. No altera la lógica de outcomes ni los perfiles.
_W = {}


def _init_worker(model_path, feature_names, batter_profiles, pitcher_profiles, n_sims, bullpen_map):
    os.environ["OMP_NUM_THREADS"] = "1"
    _W["model_path"] = model_path
    _W["fn"] = feature_names
    _W["bp"] = batter_profiles
    _W["pp"] = pitcher_profiles
    _W["ns"] = n_sims
    _W["bm"] = bullpen_map


def _sim_game(game: dict):
    bullpen = _W["bm"].get(int(game["game_pk"]), {})
    try:
        home_lineup = build_lineup_from_ids(
            team_name=game["home_team"],
            batter_ids=list(game["home_batter_ids"]),
            pitcher_id=game["home_pitcher_id"],
            batter_profiles=_W["bp"], pitcher_profiles=_W["pp"],
            bullpen_ids=bullpen.get("home"),
            reliever_entry_inning=RELIEVER_ENTRY_INNING,
        )
        away_lineup = build_lineup_from_ids(
            team_name=game["away_team"],
            batter_ids=list(game["away_batter_ids"]),
            pitcher_id=game["away_pitcher_id"],
            batter_profiles=_W["bp"], pitcher_profiles=_W["pp"],
            bullpen_ids=bullpen.get("away"),
            reliever_entry_inning=RELIEVER_ENTRY_INNING,
        )
    except ValueError:
        return None  # lineup incompleto

    sampler = ModelSampler(
        model_path=_W["model_path"],
        feature_names=_W["fn"],
        home_lineup=home_lineup,
        away_lineup=away_lineup,
        seed=SEED + int(game["game_pk"]),  # seed único por juego
    )
    wp, _, valid_sims = monte_carlo_wp(GameState(), sampler, _W["ns"])
    return {
        "game_pk":     game["game_pk"],
        "home_team":   game["home_team"],
        "away_team":   game["away_team"],
        "wp_home":     wp,
        "home_won":    game["home_won"],
        "final_score": f"{game['final_home_score']}-{game['final_away_score']}",
        "valid_sims":  valid_sims,
    }


def validate_against_test(
    model_path: Path,
    feature_names: list,
    batter_profiles: dict,
    pitcher_profiles: dict,
    lineups: pd.DataFrame,
    results: pd.DataFrame,
    bullpen_map: dict,
    n_sims: int = N_SIMS_PER_GAME,
    max_games: int = None,
    n_workers: int = None,
) -> pd.DataFrame:

    games = lineups.merge(results, on="game_pk", how="inner")
    if max_games:
        games = games.head(max_games)
    game_records = games.to_dict("records")
    n_workers = n_workers or max(1, mp.cpu_count() - 2)
    print(f"\nJuegos a validar: {len(game_records):,}  (n_sims={n_sims}, workers={n_workers})")

    initargs = (model_path, feature_names, batter_profiles, pitcher_profiles, n_sims, bullpen_map)
    with mp.Pool(n_workers, initializer=_init_worker, initargs=initargs) as pool:
        out = list(tqdm(
            pool.imap_unordered(_sim_game, game_records, chunksize=4),
            total=len(game_records), desc="Calculando WPs",
        ))

    predictions = [r for r in out if r is not None]
    return pd.DataFrame(predictions)



def evaluate_predictions(predictions: pd.DataFrame) -> dict:
    """Calcula accuracy, log loss, Brier score y baselines."""
    y_true = predictions["home_won"].values
    p_home = predictions["wp_home"].values

    p_clipped = np.clip(p_home, 1e-6, 1 - 1e-6)

    pred_class = (p_home > 0.5).astype(int)
    accuracy = (pred_class == y_true).mean()


    log_loss = -np.mean(
        y_true * np.log(p_clipped) + (1 - y_true) * np.log(1 - p_clipped)
    )


    brier = np.mean((p_home - y_true) ** 2)

    
    baseline_random_acc = max(y_true.mean(), 1 - y_true.mean())
    baseline_random_brier = np.mean((0.5 - y_true) ** 2)

    
    baseline_home_acc = y_true.mean() 
    baseline_home_p = y_true.mean()
    baseline_home_brier = np.mean((baseline_home_p - y_true) ** 2)

    return {
        "n_games":              len(predictions),
        "actual_home_win_pct":  y_true.mean(),
        "model_accuracy":       accuracy,
        "model_log_loss":       log_loss,
        "model_brier":          brier,
        "baseline_random_acc":  baseline_random_acc,
        "baseline_random_brier": baseline_random_brier,
        "baseline_home_acc":    baseline_home_acc,
        "baseline_home_brier":  baseline_home_brier,
    }


def print_evaluation_report(metrics: dict, predictions: pd.DataFrame):
    print("\n" + "=" * 70)
    print("RESULTADOS DE VALIDACIÓN")
    print("=" * 70)

    print(f"\nJuegos validados:             {metrics['n_games']:,}")
    print(f"% home wins real:             {metrics['actual_home_win_pct']*100:.1f}%")

    print("\n" + "-" * 70)
    print("MÉTRICAS DEL MODELO vs BASELINES")
    print("-" * 70)
    print(f"{'Métrica':<25} {'Modelo':>12} {'Random':>12} {'Home siempre':>15}")
    print("-" * 70)
    print(f"{'Accuracy':<25} {metrics['model_accuracy']*100:>11.1f}% "
          f"{metrics['baseline_random_acc']*100:>11.1f}% "
          f"{metrics['baseline_home_acc']*100:>14.1f}%")
    print(f"{'Brier score':<25} {metrics['model_brier']:>12.4f} "
          f"{metrics['baseline_random_brier']:>12.4f} "
          f"{metrics['baseline_home_brier']:>15.4f}")
    print(f"{'Log loss':<25} {metrics['model_log_loss']:>12.4f}")

    # Mejora sobre baselines
    print("\n" + "-" * 70)
    print("INTERPRETACIÓN")
    print("-" * 70)
    acc_vs_random = metrics['model_accuracy'] - metrics['baseline_random_acc']
    acc_vs_home   = metrics['model_accuracy'] - metrics['baseline_home_acc']
    brier_vs_home = metrics['baseline_home_brier'] - metrics['model_brier']

    print(f"  Accuracy vs random (50/50):       {acc_vs_random*100:+.2f} pp")
    print(f"  Accuracy vs 'home siempre':       {acc_vs_home*100:+.2f} pp")
    print(f"  Brier vs 'home siempre':          {brier_vs_home:+.4f}")

    print("\n  Benchmarks de la industria (para contexto):")
    print(f"    Vegas casas de apuestas:        55-58% accuracy")
    print(f"    Modelos públicos buenos:        57-60% accuracy")
    print(f"    Techo teórico (beisbol):        ~63%")

    # Distribución de predicciones
    print("\n" + "-" * 70)
    print("CALIBRACIÓN POR BUCKET DE PREDICCIÓN")
    print("-" * 70)
    buckets = [(0.0, 0.4), (0.4, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 1.0)]
    print(f"  {'Bucket':<15} {'N juegos':>10} {'WP media':>12} {'% home gana':>15}")
    for lo, hi in buckets:
        mask = (predictions["wp_home"] >= lo) & (predictions["wp_home"] < hi)
        n = mask.sum()
        if n == 0:
            continue
        wp_mean = predictions.loc[mask, "wp_home"].mean()
        actual = predictions.loc[mask, "home_won"].mean()
        gap = actual - wp_mean
        marker = "✓" if abs(gap) < 0.05 else "⚠"
        print(f"  {lo:.1f}-{hi:.1f}{'':<10} {n:>10,} {wp_mean*100:>11.1f}% "
              f"{actual*100:>14.1f}%  {marker}")



if __name__ == "__main__":
    print("=" * 70)
    print("MONTE CARLO DE WIN PROBABILITY")
    print(f"  Simulaciones por juego: {N_SIMS_PER_GAME}")
    print(f"  Seed: {SEED}")
    print("=" * 70)

    # Cargar todo
    model_path, feature_names, batter_profiles, pitcher_profiles, lineups, results, bullpen_map = load_artifacts()

    # Validar
    predictions = validate_against_test(
        model_path=model_path,
        feature_names=feature_names,
        batter_profiles=batter_profiles,
        pitcher_profiles=pitcher_profiles,
        lineups=lineups,
        results=results,
        bullpen_map=bullpen_map,
        n_sims=N_SIMS_PER_GAME,
        max_games=N_GAMES_TO_VALIDATE,
    )

    # Guardar predicciones
    out_path = MODELS_DIR / "wp_predictions.parquet"
    predictions.to_parquet(out_path, compression="snappy", index=False)
    print(f"\n  ✓ Predicciones guardadas: {out_path.name}")

    # Evaluar
    metrics = evaluate_predictions(predictions)
    print_evaluation_report(metrics, predictions)