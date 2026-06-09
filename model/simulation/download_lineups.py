"""
07_download_lineups.py
----------------------
Baja los lineups oficiales (starting batting order + starting pitcher) de
MLB Stats API para todos los juegos en el test set.

CORRE DESPUÉS de 04_split_and_encode.py.
Espera ver data/test.parquet.
Genera data/lineups.parquet con una fila por juego.

Tiempo estimado: ~10 minutos (500 juegos × 1.2 segundos por request con rate limit).
"""

import json
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
DATA_DIR = Path("./data")
CACHE_DIR = DATA_DIR / "boxscore_cache"
CACHE_DIR.mkdir(exist_ok=True)

API_BASE = "https://statsapi.mlb.com/api/v1/game"
RATE_LIMIT_SECONDS = 1.0  # ser amables con la API
TIMEOUT_SECONDS = 10


# ---------------------------------------------------------------------------
# Funciones principales
# ---------------------------------------------------------------------------
def fetch_boxscore(game_pk: int) -> Optional[dict]:
    """
    Baja el boxscore de un juego desde la API de MLB, con caché en disco.
    Si ya está en caché, lo lee del disco en lugar de pegarle a la API.
    """
    cache_path = CACHE_DIR / f"{game_pk}.json"

    # Si ya tenemos el archivo, leerlo
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    # Si no, bajarlo
    url = f"{API_BASE}/{game_pk}/boxscore"
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  ⚠️  Error en game_pk {game_pk}: {e}")
        return None

    data = response.json()

    # Guardar en caché
    with open(cache_path, "w") as f:
        json.dump(data, f)

    # Rate limiting
    time.sleep(RATE_LIMIT_SECONDS)

    return data


def extract_lineup(boxscore: dict, side: str) -> Optional[dict]:
    """
    Extrae el lineup (9 batters + pitcher abridor) de un boxscore.

    Args:
        boxscore: JSON de la API
        side: "home" o "away"

    Returns:
        dict con keys: batter_ids (lista de 9), pitcher_id, team_name
        None si no se pudo parsear
    """
    try:
        team_data = boxscore["teams"][side]
        team_name = team_data["team"]["name"]

        # batting_order es una lista de IDs (con sufijos para batting position)
        # cada ID está en formato "ID00" donde 00 es la posición en lineup
        batting_order_ids = team_data.get("battingOrder", [])

        if len(batting_order_ids) < 9:
            return None  # juego no tuvo lineup completo (raro)

        # Los IDs vienen como strings, los primeros 9 son los starters
        batter_ids = [int(bid) for bid in batting_order_ids[:9]]

        # Pitcher abridor: primer ID en la lista de pitchers
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
    """Baja y procesa un juego completo. Devuelve un dict con ambos lineups."""
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

    # Cargar test set para saber qué juegos necesitamos
    test = pd.read_parquet(DATA_DIR / "test.parquet")
    unique_games = (
        test[["game_pk", "game_date"]].drop_duplicates().reset_index(drop=True)
    )
    print(f"\nJuegos únicos en test set: {len(unique_games):,}")
    print(
        f"Rango de fechas: {unique_games['game_date'].min()} → {unique_games['game_date'].max()}"
    )

    # Contar cuántos ya están en caché
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

    # Procesar todos los juegos
    print(f"\nDescargando...")
    rows = []
    failed = []

    for _, row in tqdm(unique_games.iterrows(), total=len(unique_games)):
        result = process_game(row["game_pk"], str(row["game_date"]))
        if result is None:
            failed.append(row["game_pk"])
        else:
            rows.append(result)

    # Guardar como Parquet
    if rows:
        df = pd.DataFrame(rows)
        out_path = DATA_DIR / "lineups.parquet"
        df.to_parquet(out_path, compression="snappy", index=False)

        print(f"\n  ✓ Procesados:    {len(rows):,} juegos")
        if failed:
            print(f"  ⚠️  Fallaron:     {len(failed):,} juegos: {failed[:5]}...")
        print(f"  ✓ Guardado en:   {out_path.name}")
        print(f"  ✓ Tamaño:        {out_path.stat().st_size / 1e3:.1f} KB")

        # Sample para validar
        print(f"\nMuestra (primer juego):")
        print(df.iloc[0].to_dict())
    else:
        print("\n⚠️  No se procesó ningún juego. Revisa errores arriba.")
