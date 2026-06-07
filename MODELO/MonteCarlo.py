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

N_SIMS_PER_GAME = 200   
N_GAMES_TO_VALIDATE = None  
SEED = 42


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

    return model_path, feature_names, batter_profiles, pitcher_profiles, lineups, results



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



def validate_against_test(
    model_path: Path,
    feature_names: list,
    batter_profiles: dict,
    pitcher_profiles: dict,
    lineups: pd.DataFrame,
    results: pd.DataFrame,
    n_sims: int = N_SIMS_PER_GAME,
    max_games: int = None,
) -> pd.DataFrame:
    

    games = lineups.merge(results, on="game_pk", how="inner")
    print(f"\nJuegos a validar: {len(games):,}")

    if max_games:
        games = games.head(max_games)
        print(f"  (limitado a {max_games} para prueba rápida)")

    predictions = []

    for _, game in tqdm(games.iterrows(), total=len(games), desc="Calculando WPs"):
        # Construir lineups
        try:
            home_lineup = build_lineup_from_ids(
                team_name=game["home_team"],
                batter_ids=list(game["home_batter_ids"]),
                pitcher_id=game["home_pitcher_id"],
                batter_profiles=batter_profiles,
                pitcher_profiles=pitcher_profiles,
            )
            away_lineup = build_lineup_from_ids(
                team_name=game["away_team"],
                batter_ids=list(game["away_batter_ids"]),
                pitcher_id=game["away_pitcher_id"],
                batter_profiles=batter_profiles,
                pitcher_profiles=pitcher_profiles,
            )
        except ValueError:
            continue  # lineup incompleto


        sampler = ModelSampler(
            model_path=model_path,
            feature_names=feature_names,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            seed=SEED + int(game["game_pk"]),  # seed único por juego
        )


        initial_state = GameState()
        wp, _, valid_sims = monte_carlo_wp(initial_state, sampler, n_sims)

        predictions.append({
            "game_pk":     game["game_pk"],
            "home_team":   game["home_team"],
            "away_team":   game["away_team"],
            "wp_home":     wp,
            "home_won":    game["home_won"],
            "final_score": f"{game['final_home_score']}-{game['final_away_score']}",
            "valid_sims":  valid_sims,
        })

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
    model_path, feature_names, batter_profiles, pitcher_profiles, lineups, results = load_artifacts()

    # Validar
    predictions = validate_against_test(
        model_path=model_path,
        feature_names=feature_names,
        batter_profiles=batter_profiles,
        pitcher_profiles=pitcher_profiles,
        lineups=lineups,
        results=results,
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