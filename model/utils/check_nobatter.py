import pandas as pd
from collections import Counter
import sys

sys.path.insert(0, ".")
import importlib.util

spec = importlib.util.spec_from_file_location("ms", "Model_sampler.py")
ms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ms)

# Cargar profiles y lineups
pa_2024 = pd.read_parquet("data/pa_2024.parquet")
batter_profiles, pitcher_profiles = ms.build_player_profiles(pa_2024)
lineups = pd.read_parquet("data/lineups.parquet")

# Contar batters únicos en los lineups vs cuántos están en profiles
all_batter_ids = []
for _, row in lineups.iterrows():
    all_batter_ids.extend(row["home_batter_ids"])
    all_batter_ids.extend(row["away_batter_ids"])

unique_batters = set(all_batter_ids)
missing = [b for b in unique_batters if b not in batter_profiles]

print(f"Batters únicos en lineups de septiembre: {len(unique_batters)}")
print(f"Batters NO encontrados en profiles 2024: {len(missing)}")
print(f"Porcentaje faltante: {100 * len(missing) / len(unique_batters):.1f}%")

# Mismo análisis para pitchers
all_pitcher_ids = list(lineups["home_pitcher_id"]) + list(lineups["away_pitcher_id"])
unique_pitchers = set(all_pitcher_ids)
missing_p = [p for p in unique_pitchers if p not in pitcher_profiles]
print(f"\nPitchers únicos: {len(unique_pitchers)}")
print(f"Pitchers no encontrados: {len(missing_p)}")
print(f"Porcentaje: {100 * len(missing_p) / len(unique_pitchers):.1f}%")

# Ahora: en cuántos juegos hay AL MENOS un jugador faltante?
games_with_missing = 0
for _, row in lineups.iterrows():
    all_ids = list(row["home_batter_ids"]) + list(row["away_batter_ids"])
    if any(b not in batter_profiles for b in all_ids):
        games_with_missing += 1
print(
    f"\nJuegos con al menos 1 batter faltante: {games_with_missing}/{len(lineups)} ({100 * games_with_missing / len(lineups):.1f}%)"
)
