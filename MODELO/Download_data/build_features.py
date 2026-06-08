""" aqui buscamos relacionar las estadiscticas de cada bateador y pitcher para poder tener una aproximación
    real de que tan bien bate ciertos bateadores contra los pitchers"""

from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIR = Path("../data")

MIN_PA_BATTER = 100
MIN_PA_PITCHER = 50

LEAGUE_AVG = {
    "avg":      0.243,
    "obp":      0.312,
    "slg":      0.399,
    "iso":      0.156,
    "k_rate":   0.226,
    "bb_rate":  0.082,
    "hr_rate":  0.029,
}

def compute_batter_stats(pa_2024: pd.DataFrame) -> pd.DataFrame:


    df = pa_2024.copy()
    df["is_K"]   = (df["pa_outcome"] == "K").astype(int)
    df["is_BB"]  = (df["pa_outcome"] == "BB").astype(int)
    df["is_HBP"] = (df["pa_outcome"] == "HBP").astype(int)
    df["is_1B"]  = (df["pa_outcome"] == "1B").astype(int)
    df["is_2B"]  = (df["pa_outcome"] == "2B").astype(int)
    df["is_3B"]  = (df["pa_outcome"] == "3B").astype(int)
    df["is_HR"]  = (df["pa_outcome"] == "HR").astype(int)
    df["is_OUT"] = (df["pa_outcome"] == "OUT").astype(int)
    df["is_hit"] = df["is_1B"] + df["is_2B"] + df["is_3B"] + df["is_HR"]
    df["total_bases"] = df["is_1B"] + 2*df["is_2B"] + 3*df["is_3B"] + 4*df["is_HR"]


    grouped = df.groupby("batter").agg(
        pa_count=("batter", "size"),
        hits=("is_hit", "sum"),
        walks=("is_BB", "sum"),
        hbp=("is_HBP", "sum"),
        strikeouts=("is_K", "sum"),
        homeruns=("is_HR", "sum"),
        total_bases=("total_bases", "sum"),
    )

    grouped["at_bats"] = grouped["pa_count"] - grouped["walks"] - grouped["hbp"]
    grouped["at_bats"] = grouped["at_bats"].clip(lower=1)

    grouped["avg"]     = grouped["hits"] / grouped["at_bats"]
    grouped["obp"]     = (grouped["hits"] + grouped["walks"] + grouped["hbp"]) / grouped["pa_count"]
    grouped["slg"]     = grouped["total_bases"] / grouped["at_bats"]
    grouped["iso"]     = grouped["slg"] - grouped["avg"]
    grouped["k_rate"]  = grouped["strikeouts"] / grouped["pa_count"]
    grouped["bb_rate"] = grouped["walks"] / grouped["pa_count"]
    grouped["hr_rate"] = grouped["homeruns"] / grouped["pa_count"]

    return grouped


def compute_pitcher_stats(pa_2024: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada pitcher, calcula las stats de cómo le batearon en 2024.
    Es exactamente el mismo cálculo que para bateadores, pero agrupado por
    pitcher en lugar de batter.
    """
    df = pa_2024.copy()
    df["is_K"]   = (df["pa_outcome"] == "K").astype(int)
    df["is_BB"]  = (df["pa_outcome"] == "BB").astype(int)
    df["is_HBP"] = (df["pa_outcome"] == "HBP").astype(int)
    df["is_1B"]  = (df["pa_outcome"] == "1B").astype(int)
    df["is_2B"]  = (df["pa_outcome"] == "2B").astype(int)
    df["is_3B"]  = (df["pa_outcome"] == "3B").astype(int)
    df["is_HR"]  = (df["pa_outcome"] == "HR").astype(int)
    df["is_hit"] = df["is_1B"] + df["is_2B"] + df["is_3B"] + df["is_HR"]
    df["total_bases"] = df["is_1B"] + 2*df["is_2B"] + 3*df["is_3B"] + 4*df["is_HR"]

    grouped = df.groupby("pitcher").agg(
        pa_count=("pitcher", "size"),
        hits=("is_hit", "sum"),
        walks=("is_BB", "sum"),
        hbp=("is_HBP", "sum"),
        strikeouts=("is_K", "sum"),
        homeruns=("is_HR", "sum"),
        total_bases=("total_bases", "sum"),
    )

    grouped["at_bats"] = grouped["pa_count"] - grouped["walks"] - grouped["hbp"]
    grouped["at_bats"] = grouped["at_bats"].clip(lower=1)

    grouped["avg"]     = grouped["hits"] / grouped["at_bats"]
    grouped["obp"]     = (grouped["hits"] + grouped["walks"] + grouped["hbp"]) / grouped["pa_count"]
    grouped["slg"]     = grouped["total_bases"] / grouped["at_bats"]
    grouped["iso"]     = grouped["slg"] - grouped["avg"]
    grouped["k_rate"]  = grouped["strikeouts"] / grouped["pa_count"]
    grouped["bb_rate"] = grouped["walks"] / grouped["pa_count"]
    grouped["hr_rate"] = grouped["homeruns"] / grouped["pa_count"]

    return grouped

def apply_threshold_and_impute(
    stats: pd.DataFrame,
    min_pa: int,
    prefix: str,
) -> pd.DataFrame:
    """
    Para rookies o jugadores lesionados (con menos PA), normalizamos sus stats en el promedio de la liga
    """
    out = stats[["pa_count", "avg", "obp", "slg", "iso", "k_rate", "bb_rate", "hr_rate"]].copy()


    low_pa_mask = out["pa_count"] < min_pa
    for col in ["avg", "obp", "slg", "iso", "k_rate", "bb_rate", "hr_rate"]:
        out.loc[low_pa_mask, col] = LEAGUE_AVG[col]

    # Renombrar con prefijo
    out = out.rename(columns={c: f"{prefix}{c}" for c in out.columns})
    return out


    #Unimos las estaadisticas
def merge_features(
    pa_2025: pd.DataFrame,
    batter_stats: pd.DataFrame,
    pitcher_stats: pd.DataFrame,
) -> pd.DataFrame:

    df = pa_2025.copy()

    # Merge bateadores
    df = df.merge(batter_stats, how="left", left_on="batter", right_index=True)

    # Marcar rookies (sin entry en 2024) ANTES de imputar
    df["b_is_rookie"] = df["b_pa_count"].isna()

    # Imputar stats faltantes con promedio de liga
    for col in ["b_avg", "b_obp", "b_slg", "b_iso", "b_k_rate", "b_bb_rate", "b_hr_rate"]:
        key = col[2:]  # quitar 'b_'
        df[col] = df[col].fillna(LEAGUE_AVG[key])
    df["b_pa_count"] = df["b_pa_count"].fillna(0)

    # Merge pitchers
    df = df.merge(pitcher_stats, how="left", left_on="pitcher", right_index=True)
    df["p_is_new"] = df["p_pa_count"].isna()
    for col in ["p_avg", "p_obp", "p_slg", "p_iso", "p_k_rate", "p_bb_rate", "p_hr_rate"]:
        key = col[2:]
        df[col] = df[col].fillna(LEAGUE_AVG[key])
    df["p_pa_count"] = df["p_pa_count"].fillna(0)

    return df

def print_summary(
    pa_2025: pd.DataFrame,
    batter_stats: pd.DataFrame,
    pitcher_stats: pd.DataFrame,
    merged: pd.DataFrame,
) -> None:
    """Imprime un resumen del feature engineering."""
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"PAs en 2024 (fuente de stats): {len(batter_stats):>6,} bateadores únicos")
    print(f"                               {len(pitcher_stats):>6,} pitchers únicos")
    print(f"\nPAs en 2025 (target):          {len(pa_2025):>6,}")

    n_rookies = merged["b_is_rookie"].sum()
    n_new_p = merged["p_is_new"].sum()
    print(f"\nPAs en 2025 con rookies:       {n_rookies:>6,} ({100*n_rookies/len(merged):.1f}%)")
    print(f"PAs en 2025 con pitcher nuevo: {n_new_p:>6,} ({100*n_new_p/len(merged):.1f}%)")

    # Top 10 bateadores por PAs en 2024
    print("\nTop 10 bateadores por volumen en 2024:")
    top_b = batter_stats.nlargest(10, "pa_count")[["pa_count", "avg", "obp", "slg", "k_rate"]]
    print(top_b.to_string())

    print("\nTop 10 pitchers por volumen en 2024:")
    top_p = pitcher_stats.nlargest(10, "pa_count")[["pa_count", "avg", "k_rate", "bb_rate", "hr_rate"]]
    print(top_p.to_string())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("Construyendo features (stats agregadas 2024 → PAs 2025)")
    print("=" * 60)

    # Cargar datos
    print("\nCargando datos...")
    pa_2024 = pd.read_parquet(DATA_DIR / "pa_2024.parquet")
    pa_2025 = pd.read_parquet(DATA_DIR / "pa_2025.parquet")
    print(f"  pa_2024: {len(pa_2024):>7,} PAs")
    print(f"  pa_2025: {len(pa_2025):>7,} PAs")

    # Calcular stats agregadas
    print("\nCalculando stats de bateadores...")
    batter_stats = compute_batter_stats(pa_2024)
    print(f"  {len(batter_stats):,} bateadores únicos")

    print("\nCalculando stats de pitchers...")
    pitcher_stats = compute_pitcher_stats(pa_2024)
    print(f"  {len(pitcher_stats):,} pitchers únicos")

    # Aplicar threshold e imputar bajos PA con liga promedio
    print(f"\nAplicando threshold mínimo: bateadores={MIN_PA_BATTER}, pitchers={MIN_PA_PITCHER}")
    n_low_b = (batter_stats["pa_count"] < MIN_PA_BATTER).sum()
    n_low_p = (pitcher_stats["pa_count"] < MIN_PA_PITCHER).sum()
    print(f"  Bateadores bajo threshold: {n_low_b} (regresan a liga promedio)")
    print(f"  Pitchers bajo threshold:   {n_low_p} (regresan a liga promedio)")

    batter_features = apply_threshold_and_impute(batter_stats, MIN_PA_BATTER, "b_")
    pitcher_features = apply_threshold_and_impute(pitcher_stats, MIN_PA_PITCHER, "p_")

    # Unir features a los PAs de 2025
    print("\nUniendo features a PAs de 2025...")
    merged = merge_features(pa_2025, batter_features, pitcher_features)

    # Reporte final
    print_summary(pa_2025, batter_stats, pitcher_stats, merged)

    # Guardar
    out_path = DATA_DIR / "pa_2025_with_features.parquet"
    merged.to_parquet(out_path, compression="snappy", index=False)
    size_mb = out_path.stat().st_size / 1e6
    print(f"\nGuardado: {out_path.name} ({size_mb:.1f} MB)")
    print(f"Columnas: {merged.shape[1]}")
    print(f"Filas:    {len(merged):,}")

