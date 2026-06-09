from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import log_loss, accuracy_score, confusion_matrix

DATA_DIR = Path("../data")
# Path canónico de modelos (MODELO/models), de donde leen predict.py y MonteCarlo.py.
MODELS_DIR = Path("./models")
MODELS_DIR.mkdir(exist_ok=True)


OUTCOME_ORDER = ["K", "BB", "HBP", "1B", "2B", "3B", "HR", "OUT", "DP", "SF"]
NUM_CLASSES = len(OUTCOME_ORDER)


LGB_PARAMS = {
    "objective": "multiclass",
    "num_class": NUM_CLASSES,
    "metric": "multi_logloss",
    "learning_rate": 0.05,
    "num_leaves": 63,
    "min_data_in_leaf": 100,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.9,
    "bagging_freq": 5,
    "lambda_l2": 0.1,
    "verbose": -1,
    "seed": 42,
}

NUM_BOOST_ROUNDS = 1000
EARLY_STOPPING_ROUNDS = 50


def load_splits():
    print("Cargando splits...")
    train = pd.read_parquet(DATA_DIR / "train.parquet")
    val = pd.read_parquet(DATA_DIR / "val.parquet")
    test = pd.read_parquet(DATA_DIR / "test.parquet")
    print(f"  train: {len(train):>7,} filas")
    print(f"  val:   {len(val):>7,} filas")
    print(f"  test:  {len(test):>7,} filas")

    feature_names = pd.read_csv(DATA_DIR / "feature_names.csv", header=None)[0].tolist()
    print(f"  features: {len(feature_names)}")
    return train, val, test, feature_names


def split_xy(df, feature_names):
    """Separa features (X) y target (y) en arrays."""
    X = df[feature_names].values
    y = df["target"].values
    return X, y


def train_model(X_train, y_train, X_val, y_val, feature_names):
    print("\n" + "=" * 60)
    print("Entrenando LightGBM multiclase")
    print("=" * 60)
    print(f"  Hiperparámetros principales:")
    for k in ["learning_rate", "num_leaves", "min_data_in_leaf", "lambda_l2"]:
        print(f"    {k:<22} {LGB_PARAMS[k]}")
    print(f"  Max rondas: {NUM_BOOST_ROUNDS}")
    print(f"  Early stopping: {EARLY_STOPPING_ROUNDS} rondas sin mejora")

    train_set = lgb.Dataset(X_train, label=y_train, feature_name=feature_names)
    val_set = lgb.Dataset(
        X_val, label=y_val, feature_name=feature_names, reference=train_set
    )

    print("\nEntrenando...")
    model = lgb.train(
        params=LGB_PARAMS,
        train_set=train_set,
        num_boost_round=NUM_BOOST_ROUNDS,
        valid_sets=[train_set, val_set],
        valid_names=["train", "val"],
        callbacks=[
            lgb.early_stopping(EARLY_STOPPING_ROUNDS),
            lgb.log_evaluation(50),
        ],
    )
    print(f"\nMejor iteración: {model.best_iteration}")
    return model


def baseline_uniform(y_train, y_test):
    """Predice la distribución uniforme (1/8 para cada clase). Worst case."""
    pred = np.full((len(y_test), NUM_CLASSES), 1.0 / NUM_CLASSES)
    return log_loss(y_test, pred, labels=list(range(NUM_CLASSES)))


def baseline_league_avg(y_train, y_test):
    """Predice la distribución promedio del train set. Baseline natural."""
    train_freqs = np.bincount(y_train, minlength=NUM_CLASSES) / len(y_train)
    pred = np.tile(train_freqs, (len(y_test), 1))
    return log_loss(y_test, pred, labels=list(range(NUM_CLASSES)))


def evaluate(model, X, y, name):
    """Predice y reporta log loss + accuracy en un set dado."""
    pred_proba = model.predict(X, num_iteration=model.best_iteration)
    pred_class = pred_proba.argmax(axis=1)
    ll = log_loss(y, pred_proba, labels=list(range(NUM_CLASSES)))
    acc = accuracy_score(y, pred_class)
    print(f"  {name:<10} log_loss={ll:.4f}  accuracy={acc:.4f}")
    return ll, acc, pred_proba


def print_distribution_comparison(y_true, pred_proba):
    """Compara distribución real vs distribución predicha promedio en test."""
    print("\n" + "-" * 60)
    print("  Distribución real vs predicha (promedio en test)")
    print("-" * 60)
    print(f"  {'Clase':<6} {'Real':>8} {'Predicho':>10} {'Δ':>8}")
    print(f"  {'-' * 40}")
    true_freqs = np.bincount(y_true, minlength=NUM_CLASSES) / len(y_true)
    pred_freqs = pred_proba.mean(axis=0)
    for i, outcome in enumerate(OUTCOME_ORDER):
        print(
            f"  {outcome:<6} {true_freqs[i] * 100:>7.2f}% {pred_freqs[i] * 100:>9.2f}% "
            f"{(pred_freqs[i] - true_freqs[i]) * 100:>+7.2f}%"
        )


def print_feature_importance(model, feature_names, top_n=15):
    """Imprime las features más importantes según ganancia acumulada."""
    importance = model.feature_importance(importance_type="gain")
    fi = pd.DataFrame(
        {
            "feature": feature_names,
            "gain": importance,
        }
    ).sort_values("gain", ascending=False)

    print("\n" + "-" * 60)
    print(f"  Top {top_n} features por ganancia (importancia)")
    print("-" * 60)
    fi["pct"] = 100 * fi["gain"] / fi["gain"].sum()
    fi["cum_pct"] = fi["pct"].cumsum()
    for i, row in fi.head(top_n).iterrows():
        print(
            f"  {row['feature']:<20} gain={row['gain']:>12,.0f} "
            f"({row['pct']:>5.2f}%)  acum={row['cum_pct']:>5.1f}%"
        )

    return fi


def print_confusion_matrix(y_true, pred_proba):
    """Matriz de confusión (etiqueta verdadera vs predicha)."""
    pred_class = pred_proba.argmax(axis=1)
    cm = confusion_matrix(y_true, pred_class, labels=list(range(NUM_CLASSES)))
    print("\n" + "-" * 60)
    print("  Matriz de confusión (filas=real, cols=predicho)")
    print("-" * 60)
    print(f"  {'':<6}" + "".join(f"{o:>7}" for o in OUTCOME_ORDER))
    for i, outcome in enumerate(OUTCOME_ORDER):
        row_total = cm[i].sum()
        row_str = "".join(f"{cm[i, j]:>7,}" for j in range(NUM_CLASSES))
        print(f"  {outcome:<6}{row_str}  (n={row_total:,})")


def diagnostic_model_discrimination(
    model,
    test_df: pd.DataFrame,
    feature_names: list,
    pred_proba: np.ndarray,
):
    """
    Diagnósticos detallados de qué tanto el modelo discrimina entre
    situaciones distintas. Imprime ejemplos concretos y comparaciones.
    """
    print("\n" + "=" * 60)
    print("DIAGNÓSTICO: ¿El modelo discrimina entre situaciones?")
    print("=" * 60)

    # -----------------------------------------------------------------
    # 1. Predicciones para PAs específicos del test set
    # -----------------------------------------------------------------
    print("\n[1] Ejemplos de predicciones del test set:")
    print("-" * 60)

    # Indexar test con la predicción correspondiente
    test_reset = test_df.reset_index(drop=True)

    # Encontrar 4 PAs con perfiles muy distintos
    examples = []

    # PA con bateador de alto K_rate vs pitcher de alto K_rate
    high_k_mask = (test_reset["b_k_rate"] > 0.30) & (test_reset["p_k_rate"] > 0.28)
    if high_k_mask.any():
        idx = test_reset[high_k_mask].index[0]
        examples.append(("Alto K bateador vs Alto K pitcher", idx))

    # PA con bateador de bajo K_rate vs pitcher de bajo K_rate
    low_k_mask = (test_reset["b_k_rate"] < 0.15) & (test_reset["p_k_rate"] < 0.18)
    if low_k_mask.any():
        idx = test_reset[low_k_mask].index[0]
        examples.append(("Bajo K bateador vs Bajo K pitcher", idx))

    # PA con bateador de alto poder
    high_power_mask = (test_reset["b_iso"] > 0.250) & (test_reset["b_hr_rate"] > 0.05)
    if high_power_mask.any():
        idx = test_reset[high_power_mask].index[0]
        examples.append(("Bateador de alto poder", idx))

    # PA con rookie
    rookie_mask = test_reset["b_is_rookie"] == 1
    if rookie_mask.any():
        idx = test_reset[rookie_mask].index[0]
        examples.append(("Bateador rookie", idx))

    for label, idx in examples:
        row = test_reset.loc[idx]
        probs = pred_proba[idx]
        actual = row["pa_outcome"]
        print(f"\n  {label}:")
        print(
            f"    b_k_rate={row['b_k_rate']:.3f}  b_iso={row['b_iso']:.3f}  "
            f"b_hr_rate={row['b_hr_rate']:.3f}"
        )
        print(
            f"    p_k_rate={row['p_k_rate']:.3f}  p_avg={row['p_avg']:.3f}  "
            f"p_hr_rate={row['p_hr_rate']:.3f}"
        )
        print(f"    Real: {actual}")
        print(f"    Modelo predice:")
        for i, outcome in enumerate(OUTCOME_ORDER):
            bar = "█" * int(probs[i] * 50)
            print(f"      {outcome:<4} {probs[i] * 100:>5.2f}%  {bar}")

    # -----------------------------------------------------------------
    # 2. Predicciones sintéticas: aislar efecto de calidad de jugadores
    # -----------------------------------------------------------------
    print("\n\n[2] Escenarios sintéticos (mismo contexto, distintos jugadores):")
    print("-" * 60)

    # Tomamos un PA "base" del test y modificamos las stats de jugadores
    base_row = test_reset.iloc[0].copy()
    base_features = base_row[feature_names].values.astype(float)

    scenarios = {
        "Elite batter vs Elite pitcher": {
            "b_k_rate": 0.12,
            "b_bb_rate": 0.13,
            "b_avg": 0.310,
            "b_obp": 0.420,
            "b_slg": 0.580,
            "b_iso": 0.270,
            "b_hr_rate": 0.060,
            "p_k_rate": 0.32,
            "p_bb_rate": 0.05,
            "p_avg": 0.200,
            "p_obp": 0.260,
            "p_slg": 0.320,
            "p_iso": 0.120,
            "p_hr_rate": 0.018,
        },
        "Elite batter vs Bad pitcher": {
            "b_k_rate": 0.12,
            "b_bb_rate": 0.13,
            "b_avg": 0.310,
            "b_obp": 0.420,
            "b_slg": 0.580,
            "b_iso": 0.270,
            "b_hr_rate": 0.060,
            "p_k_rate": 0.16,
            "p_bb_rate": 0.11,
            "p_avg": 0.280,
            "p_obp": 0.360,
            "p_slg": 0.490,
            "p_iso": 0.210,
            "p_hr_rate": 0.045,
        },
        "Bad batter vs Elite pitcher": {
            "b_k_rate": 0.32,
            "b_bb_rate": 0.05,
            "b_avg": 0.200,
            "b_obp": 0.260,
            "b_slg": 0.320,
            "b_iso": 0.120,
            "b_hr_rate": 0.012,
            "p_k_rate": 0.32,
            "p_bb_rate": 0.05,
            "p_avg": 0.200,
            "p_obp": 0.260,
            "p_slg": 0.320,
            "p_iso": 0.120,
            "p_hr_rate": 0.018,
        },
        "Average batter vs Average pitcher": {
            "b_k_rate": 0.226,
            "b_bb_rate": 0.082,
            "b_avg": 0.243,
            "b_obp": 0.312,
            "b_slg": 0.399,
            "b_iso": 0.156,
            "b_hr_rate": 0.029,
            "p_k_rate": 0.226,
            "p_bb_rate": 0.082,
            "p_avg": 0.243,
            "p_obp": 0.312,
            "p_slg": 0.399,
            "p_iso": 0.156,
            "p_hr_rate": 0.029,
        },
    }

    # Para hacer las predicciones, modificamos solo las columnas relevantes
    fname_to_idx = {name: i for i, name in enumerate(feature_names)}

    synthetic_preds = {}
    for label, overrides in scenarios.items():
        features = base_features.copy()
        for col, val in overrides.items():
            if col in fname_to_idx:
                features[fname_to_idx[col]] = val
        probs = model.predict(
            features.reshape(1, -1), num_iteration=model.best_iteration
        )[0]
        synthetic_preds[label] = probs

    # Imprimir tabla comparativa
    print(f"\n  {'Outcome':<6}", end="")
    for label in scenarios:
        short = (
            label.replace(" vs ", " v ")
            .replace("Elite", "Elt")
            .replace("Average", "Avg")
            .replace("Bad", "Bad")
        )
        print(f"{short[:18]:>18}", end="")
    print()
    print("  " + "-" * (6 + 18 * len(scenarios)))

    for i, outcome in enumerate(OUTCOME_ORDER):
        print(f"  {outcome:<6}", end="")
        for label in scenarios:
            pct = synthetic_preds[label][i] * 100
            print(f"{pct:>17.2f}%", end="")
        print()

    # -----------------------------------------------------------------
    # 3. Predicciones agrupadas por calidad de pitcher
    # -----------------------------------------------------------------
    print("\n\n[3] Predicciones promedio por calidad de pitcher (test set):")
    print("-" * 60)

    # Dividir el test set por percentiles de p_k_rate
    p_k_rate_test = test_reset["p_k_rate"].values
    q33 = np.quantile(p_k_rate_test, 0.33)
    q67 = np.quantile(p_k_rate_test, 0.67)

    groups = {
        "Pitchers malos (K% bajo)": p_k_rate_test < q33,
        "Pitchers promedio": (p_k_rate_test >= q33) & (p_k_rate_test < q67),
        "Pitchers buenos (K% alto)": p_k_rate_test >= q67,
    }

    print(f"\n  {'Outcome':<6}", end="")
    for label in groups:
        print(f"{label[:22]:>22}", end="")
    print()
    print("  " + "-" * (6 + 22 * len(groups)))

    for i, outcome in enumerate(OUTCOME_ORDER):
        print(f"  {outcome:<6}", end="")
        for label, mask in groups.items():
            mean_pct = pred_proba[mask, i].mean() * 100
            print(f"{mean_pct:>21.2f}%", end="")
        print()


if __name__ == "__main__":
    train, val, test, feature_names = load_splits()

    # Preparar X/y
    X_train, y_train = split_xy(train, feature_names)
    X_val, y_val = split_xy(val, feature_names)
    X_test, y_test = split_xy(test, feature_names)

    model = train_model(X_train, y_train, X_val, y_val, feature_names)

    print("\n" + "=" * 60)
    print("EVALUACIÓN")
    print("=" * 60)

    print("\n  Baselines (para contexto):")
    ll_uniform = baseline_uniform(y_train, y_test)
    ll_league = baseline_league_avg(y_train, y_test)
    print(f"  {'uniforme':<10} log_loss={ll_uniform:.4f}  (worst case, 1/8 cada clase)")
    print(
        f"  {'liga avg':<10} log_loss={ll_league:.4f}  (predecir frecuencia de train siempre)"
    )

    print("\n  Modelo entrenado:")
    ll_train, _, _ = evaluate(model, X_train, y_train, "train")
    ll_val, _, _ = evaluate(model, X_val, y_val, "val")
    ll_test, acc_test, pred_test = evaluate(model, X_test, y_test, "test")

    print("\n  Ganancia del modelo sobre baselines:")
    improve_uniform = (ll_uniform - ll_test) / ll_uniform * 100
    improve_league = (ll_league - ll_test) / ll_league * 100
    print(f"    vs uniforme:   {improve_uniform:+.2f}%")
    print(f"    vs liga avg:   {improve_league:+.2f}%   ← este es el que importa")

    print_distribution_comparison(y_test, pred_test)
    fi = print_feature_importance(model, feature_names)
    print_confusion_matrix(y_test, pred_test)
    diagnostic_model_discrimination(model, test, feature_names, pred_test)

    print("\n" + "=" * 60)
    print("Guardando artefactos...")
    print("=" * 60)

    model.save_model(MODELS_DIR / "pa_model.txt")
    print(f"  ✓ modelo:    models/pa_model.txt")

    pred_df = pd.DataFrame(pred_test, columns=[f"p_{o}" for o in OUTCOME_ORDER])
    pred_df["target"] = y_test
    pred_df["pa_outcome"] = test["pa_outcome"].values
    pred_df.to_parquet(MODELS_DIR / "predictions_test.parquet", index=False)
    print(f"  ✓ predicciones test: models/predictions_test.parquet")

    fi.to_csv(MODELS_DIR / "feature_importance.csv", index=False)
    print(f"  ✓ feature importance: models/feature_importance.csv")

    print("\nListo. El modelo está entrenado y guardado.")
