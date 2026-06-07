from pathlib import Path
 
import numpy as np
import pandas as pd

DATA_DIR = Path("./data")
 
# Fechas de corte del split temporal
TRAIN_END = "2025-07-31"   # train: hasta fin de julio
VAL_END   = "2025-08-31"

def encode_features(df: pd.DataFrame) -> pd.DataFrame:
    df=df.copy()
    
    
    # p_throws: L o R → 0 o 1
    df["p_throws_R"] = (df["p_throws"] == "R").astype(int)
    # stand: L, R o S (switch) → 3 columnas separadas
    df["stand_R"] = (df["stand"] == "R").astype(int)
    df["stand_S"] = (df["stand"] == "S").astype(int)
    
    df["is_top"] = (df["inning_topbot"] == "Top").astype(int)
    
    df["score_diff"] = df["bat_score"] - df["fld_score"]
    
    same_handed = (
        ((df["stand"] == "R") & (df["p_throws"] == "R")) |
        ((df["stand"] == "L") & (df["p_throws"] == "L"))
    )
    df["same_handed"] = same_handed.astype(int)
    
    df["bases_state"] = (
        df["on_1b"].astype(int) +
        df["on_2b"].astype(int) * 2 +
        df["on_3b"].astype(int) * 4
    )
    
    df["b_is_rookie"] = df["b_is_rookie"].astype(int)
    df["p_is_new"]    = df["p_is_new"].astype(int)
    
    outcome_order = ["K", "BB", "HBP", "1B", "2B", "3B", "HR", "OUT"]
    outcome_to_int = {o: i for i, o in enumerate(outcome_order)}
    df["target"] = df["pa_outcome"].map(outcome_to_int)
    
    return df


def select_model_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    feature_cols = [
        # Manos / matchup
        "p_throws_R", "stand_R", "stand_S", "same_handed",
        # Game state
        "inning", "is_top", "outs_when_up", "bases_state", "score_diff",
        # Stats del bateador
        "b_pa_count", "b_avg", "b_obp", "b_slg", "b_iso",
        "b_k_rate", "b_bb_rate", "b_hr_rate", "b_is_rookie",
        # Stats del pitcher
        "p_pa_count", "p_avg", "p_obp", "p_slg", "p_iso",
        "p_k_rate", "p_bb_rate", "p_hr_rate", "p_is_new",
    ]
    
    keep_cols = feature_cols + ["target", "game_pk", "game_date", "pitcher", "batter", "pa_outcome"]
    
    return df[keep_cols].copy(), feature_cols


def temporal_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    df["game_date"] = pd.to_datetime(df["game_date"])
 
    train = df[df["game_date"] <= TRAIN_END].copy()
    val   = df[(df["game_date"] > TRAIN_END) & (df["game_date"] <= VAL_END)].copy()
    test  = df[df["game_date"] > VAL_END].copy()
 
    return train, val, test

def print_split_report(train, val, test, feature_cols):
    print("\n" + "=" * 60)
    print("RESUMEN DEL SPLIT")
    print("=" * 60)
 
    total = len(train) + len(val) + len(test)
    for name, split in [("TRAIN", train), ("VAL", val), ("TEST", test)]:
        n = len(split)
        pct = 100 * n / total
        dmin = split["game_date"].min().strftime("%Y-%m-%d")
        dmax = split["game_date"].max().strftime("%Y-%m-%d")
        print(f"  {name:<6} {n:>7,} PAs ({pct:>4.1f}%)  |  {dmin} → {dmax}")
 
    print(f"\nFeatures del modelo: {len(feature_cols)}")
    for col in feature_cols:
        print(f"  - {col}")
 
    # Distribución de outcomes por split (sanity check: deben ser similares)
    print("\nDistribución de outcomes por split (debería ser similar):")
    print(f"  {'Clase':<6} {'Train':>8} {'Val':>8} {'Test':>8}")
    print(f"  {'-' * 35}")
    for outcome in ["K", "BB", "HBP", "1B", "2B", "3B", "HR", "OUT"]:
        t_pct = (train["pa_outcome"] == outcome).mean() * 100
        v_pct = (val["pa_outcome"] == outcome).mean() * 100
        te_pct = (test["pa_outcome"] == outcome).mean() * 100
        print(f"  {outcome:<6} {t_pct:>7.2f}% {v_pct:>7.2f}% {te_pct:>7.2f}%")
 
 
# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("Split temporal + codificación final de features")
    print("=" * 60)
 
    # Cargar
    print("\nCargando pa_2025_with_features.parquet...")
    df = pd.read_parquet(DATA_DIR / "pa_2025_with_features.parquet")
    print(f"  {len(df):,} PAs, {df.shape[1]} columnas")
 
    # Codificar features
    print("\nCodificando features categóricas y derivando nuevas...")
    df = encode_features(df)
 
    # Seleccionar solo las columnas que el modelo necesita
    df, feature_cols = select_model_columns(df)
    print(f"  Features finales: {len(feature_cols)}")
 
    # Split temporal
    print(f"\nHaciendo split temporal...")
    print(f"  Train: hasta {TRAIN_END}")
    print(f"  Val:   {TRAIN_END} → {VAL_END}")
    print(f"  Test:  después de {VAL_END}")
    train, val, test = temporal_split(df)
 
    # Reporte
    print_split_report(train, val, test, feature_cols)
 
    # Guardar
    print("\nGuardando splits...")
    train.to_parquet(DATA_DIR / "train.parquet", compression="snappy", index=False)
    val.to_parquet(DATA_DIR / "val.parquet", compression="snappy", index=False)
    test.to_parquet(DATA_DIR / "test.parquet", compression="snappy", index=False)
 
    # Guardar también la lista de features para el script de training
    pd.Series(feature_cols).to_csv(DATA_DIR / "feature_names.csv", index=False, header=False)
 
    print(f"  ✓ train.parquet ({len(train):,} filas)")
    print(f"  ✓ val.parquet   ({len(val):,} filas)")
    print(f"  ✓ test.parquet  ({len(test):,} filas)")
    print(f"  ✓ feature_names.csv (lista de {len(feature_cols)} features)")
 
    print("\n" + "=" * 60)
    print("Listo para entrenar el modelo.")
    print("=" * 60)