"""Here we relate the stats of each batter and pitcher to get a realistic
approximation of how well certain batters hit against pitchers."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Shared client for official MLB stats (lives in Simulation/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Simulation"))
import mlb_stats

DATA_DIR = Path("../data")

# SOURCE season for the player stats. Must be BEFORE the labels
# (the labels are 2025 PAs) so we don't leak future information.
SOURCE_SEASON = 2024

MIN_PA_BATTER = 100
MIN_PA_PITCHER = 50

LEAGUE_AVG = {
    "avg": 0.243,
    "obp": 0.312,
    "slg": 0.399,
    "iso": 0.156,
    "k_rate": 0.226,
    "bb_rate": 0.082,
    "hr_rate": 0.029,
}


def apply_threshold_and_impute(
    stats: pd.DataFrame,
    min_pa: int,
    prefix: str,
) -> pd.DataFrame:
    """
    For rookies or injured players (with fewer PA), we normalize their stats to the league average.
    """
    out = stats[
        ["pa_count", "avg", "obp", "slg", "iso", "k_rate", "bb_rate", "hr_rate"]
    ].copy()

    low_pa_mask = out["pa_count"] < min_pa
    for col in ["avg", "obp", "slg", "iso", "k_rate", "bb_rate", "hr_rate"]:
        out.loc[low_pa_mask, col] = LEAGUE_AVG[col]

    # Rename with prefix
    out = out.rename(columns={c: f"{prefix}{c}" for c in out.columns})
    return out

    # We join the stats


def merge_features(
    pa_2025: pd.DataFrame,
    batter_stats: pd.DataFrame,
    pitcher_stats: pd.DataFrame,
) -> pd.DataFrame:
    """Merge batter and pitcher features onto the 2025 PAs, flagging and imputing missing players."""
    df = pa_2025.copy()

    # Merge batters
    df = df.merge(batter_stats, how="left", left_on="batter", right_index=True)

    # Flag rookies (no entry in 2024) BEFORE imputing
    df["b_is_rookie"] = df["b_pa_count"].isna()

    # Impute missing stats with league average
    for col in [
        "b_avg",
        "b_obp",
        "b_slg",
        "b_iso",
        "b_k_rate",
        "b_bb_rate",
        "b_hr_rate",
    ]:
        key = col[2:]  # strip 'b_'
        df[col] = df[col].fillna(LEAGUE_AVG[key])
    df["b_pa_count"] = df["b_pa_count"].fillna(0)

    # Merge pitchers
    df = df.merge(pitcher_stats, how="left", left_on="pitcher", right_index=True)
    df["p_is_new"] = df["p_pa_count"].isna()
    for col in [
        "p_avg",
        "p_obp",
        "p_slg",
        "p_iso",
        "p_k_rate",
        "p_bb_rate",
        "p_hr_rate",
    ]:
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
    """Print a summary of the feature engineering."""
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"PAs en 2024 (fuente de stats): {len(batter_stats):>6,} bateadores únicos")
    print(f"                               {len(pitcher_stats):>6,} pitchers únicos")
    print(f"\nPAs en 2025 (target):          {len(pa_2025):>6,}")

    n_rookies = merged["b_is_rookie"].sum()
    n_new_p = merged["p_is_new"].sum()
    print(
        f"\nPAs en 2025 con rookies:       {n_rookies:>6,} ({100 * n_rookies / len(merged):.1f}%)"
    )
    print(
        f"PAs en 2025 con pitcher nuevo: {n_new_p:>6,} ({100 * n_new_p / len(merged):.1f}%)"
    )

    # Top 10 batters by PAs in 2024
    print("\nTop 10 bateadores por volumen en 2024:")
    top_b = batter_stats.nlargest(10, "pa_count")[
        ["pa_count", "avg", "obp", "slg", "k_rate"]
    ]
    print(top_b.to_string())

    print("\nTop 10 pitchers por volumen en 2024:")
    top_p = pitcher_stats.nlargest(10, "pa_count")[
        ["pa_count", "avg", "k_rate", "bb_rate", "hr_rate"]
    ]
    print(top_p.to_string())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print(f"Construyendo features (stats OFICIALES MLB {SOURCE_SEASON} → PAs 2025)")
    print("=" * 60)

    # Load the target PAs (the labels + the game context). The player stats
    # are NO LONGER computed here: they come official from MLB via mlb_stats.
    print("\nCargando PAs 2025 (target)...")
    pa_2025 = pd.read_parquet(DATA_DIR / "pa_2025.parquet")
    print(f"  pa_2025: {len(pa_2025):>7,} PAs")

    # Official MLB stats from the source season (cached download).
    print(f"\nDescargando stats oficiales de MLB ({SOURCE_SEASON})...")
    batter_stats = mlb_stats.batter_frame(SOURCE_SEASON)
    pitcher_stats = mlb_stats.pitcher_frame(SOURCE_SEASON)
    print(f"  {len(batter_stats):,} bateadores con stats oficiales")
    print(f"  {len(pitcher_stats):,} pitchers con stats oficiales")

    # Apply threshold and impute low-PA players with league average
    print(
        f"\nAplicando threshold mínimo: bateadores={MIN_PA_BATTER}, pitchers={MIN_PA_PITCHER}"
    )
    n_low_b = (batter_stats["pa_count"] < MIN_PA_BATTER).sum()
    n_low_p = (pitcher_stats["pa_count"] < MIN_PA_PITCHER).sum()
    print(f"  Bateadores bajo threshold: {n_low_b} (regresan a liga promedio)")
    print(f"  Pitchers bajo threshold:   {n_low_p} (regresan a liga promedio)")

    batter_features = apply_threshold_and_impute(batter_stats, MIN_PA_BATTER, "b_")
    pitcher_features = apply_threshold_and_impute(pitcher_stats, MIN_PA_PITCHER, "p_")

    # Join features to the 2025 PAs
    print("\nUniendo features a PAs de 2025...")
    merged = merge_features(pa_2025, batter_features, pitcher_features)

    # Final report
    print_summary(pa_2025, batter_stats, pitcher_stats, merged)

    # Save
    out_path = DATA_DIR / "pa_2025_with_features.parquet"
    merged.to_parquet(out_path, compression="snappy", index=False)
    size_mb = out_path.stat().st_size / 1e6
    print(f"\nGuardado: {out_path.name} ({size_mb:.1f} MB)")
    print(f"Columnas: {merged.shape[1]}")
    print(f"Filas:    {len(merged):,}")
