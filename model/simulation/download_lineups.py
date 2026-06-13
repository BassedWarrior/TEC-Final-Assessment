"""
07_download_lineups.py
----------------------
Downloads the official lineups (starting batting order + starting pitcher) from
the MLB Stats API for every game in the test set.

RUNS AFTER 04_split_and_encode.py.
Expects data/test.parquet to exist.
Produces data/lineups.parquet with one row per game.

Estimated time: ~10 minutes (500 games × 1.2 seconds per request with rate limit).
"""

import json
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_DIR = Path("./data")
CACHE_DIR = DATA_DIR / "boxscore_cache"
CACHE_DIR.mkdir(exist_ok=True)

API_BASE = "https://statsapi.mlb.com/api/v1/game"
RATE_LIMIT_SECONDS = 1.0  # be nice to the API
TIMEOUT_SECONDS = 10


# ---------------------------------------------------------------------------
# Main functions
# ---------------------------------------------------------------------------
def fetch_boxscore(game_pk: int) -> Optional[dict]:
    """
    Download a game's boxscore from the MLB API, with on-disk cache.
    If already cached, read it from disk instead of hitting the API.
    """
    cache_path = CACHE_DIR / f"{game_pk}.json"

    # If we already have the file, read it
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    # Otherwise, download it
    url = f"{API_BASE}/{game_pk}/boxscore"
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  ⚠️  Error en game_pk {game_pk}: {e}")
        return None

    data = response.json()

    # Save to cache
    with open(cache_path, "w") as f:
        json.dump(data, f)

    # Rate limiting
    time.sleep(RATE_LIMIT_SECONDS)

    return data


def extract_lineup(boxscore: dict, side: str) -> Optional[dict]:
    """
    Extract the lineup (9 batters + starting pitcher) from a boxscore.

    Args:
        boxscore: API JSON
        side: "home" or "away"

    Returns:
        dict with keys: batter_ids (list of 9), pitcher_id, team_name
        None if it could not be parsed
    """
    try:
        team_data = boxscore["teams"][side]
        team_name = team_data["team"]["name"]

        # batting_order is a list of IDs (with suffixes for batting position)
        # each ID is in the format "ID00" where 00 is the position in the lineup
        batting_order_ids = team_data.get("battingOrder", [])

        if len(batting_order_ids) < 9:
            return None  # game did not have a complete lineup (rare)

        # The IDs come as strings; the first 9 are the starters
        batter_ids = [int(bid) for bid in batting_order_ids[:9]]

        # Starting pitcher: first ID in the pitchers list
        pitcher_ids = team_data.get("pitchers", [])
        if not pitcher_ids:
            return None
        pitcher_id = int(pitcher_ids[0])

        return {
            "team_name": team_name,
            "batter_ids": batter_ids,
            "pitcher_id": pitcher_id,
        }
    except (KeyError, ValueError, IndexError) as e:
        return None


def process_game(game_pk: int, game_date: str) -> Optional[dict]:
    """Download and process a full game. Returns a dict with both lineups."""
    boxscore = fetch_boxscore(game_pk)
    if boxscore is None:
        return None

    home = extract_lineup(boxscore, "home")
    away = extract_lineup(boxscore, "away")

    if home is None or away is None:
        return None

    return {
        "game_pk": game_pk,
        "game_date": game_date,
        "home_team": home["team_name"],
        "away_team": away["team_name"],
        "home_batter_ids": home["batter_ids"],
        "home_pitcher_id": home["pitcher_id"],
        "away_batter_ids": away["batter_ids"],
        "away_pitcher_id": away["pitcher_id"],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("Bajando lineups oficiales desde MLB Stats API")
    print("=" * 60)

    # Load the test set to know which games we need
    test = pd.read_parquet(DATA_DIR / "test.parquet")
    unique_games = (
        test[["game_pk", "game_date"]].drop_duplicates().reset_index(drop=True)
    )
    print(f"\nJuegos únicos en test set: {len(unique_games):,}")
    print(
        f"Rango de fechas: {unique_games['game_date'].min()} → {unique_games['game_date'].max()}"
    )

    # Count how many are already cached
    cached = sum(
        1
        for _, row in unique_games.iterrows()
        if (CACHE_DIR / f"{row['game_pk']}.json").exists()
    )
    print(f"En caché:        {cached:,}")
    print(f"A descargar:     {len(unique_games) - cached:,}")
    print(
        f"Tiempo estimado: ~{(len(unique_games) - cached) * RATE_LIMIT_SECONDS / 60:.1f} minutos"
    )

    # Process all games
    print(f"\nDescargando...")
    rows = []
    failed = []

    for _, row in tqdm(unique_games.iterrows(), total=len(unique_games)):
        result = process_game(row["game_pk"], str(row["game_date"]))
        if result is None:
            failed.append(row["game_pk"])
        else:
            rows.append(result)

    # Save as Parquet
    if rows:
        df = pd.DataFrame(rows)
        out_path = DATA_DIR / "lineups.parquet"
        df.to_parquet(out_path, compression="snappy", index=False)

        print(f"\n  ✓ Procesados:    {len(rows):,} juegos")
        if failed:
            print(f"  ⚠️  Fallaron:     {len(failed):,} juegos: {failed[:5]}...")
        print(f"  ✓ Guardado en:   {out_path.name}")
        print(f"  ✓ Tamaño:        {out_path.stat().st_size / 1e3:.1f} KB")

        # Sample to validate
        print(f"\nMuestra (primer juego):")
        print(df.iloc[0].to_dict())
    else:
        print("\n⚠️  No se procesó ningún juego. Revisa errores arriba.")
