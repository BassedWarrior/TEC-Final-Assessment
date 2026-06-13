import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from pybaseball import statcast


DATA_DIR = Path("../data")
DATA_DIR.mkdir(exist_ok=True)

# Regular-season date ranges (approximate — pybaseball filters the real ones)
SEASONS = {
    2024: ("2024-03-28", "2024-09-29"),
    2025: ("2025-03-27", "2025-09-28"),
}

# We download in small windows with retries. A single statcast() call for the
# whole season fires dozens of requests in parallel; if ONE returns an error
# message (rate-limit), pybaseball blows up the entire download. With windows,
# a transient failure only retries that window.
CHUNK_DAYS = 14
MAX_RETRIES = 4
RETRY_SLEEP = 5  # seconds, with linear backoff


def _statcast_chunk(start_date: str, end_date: str) -> pd.DataFrame:
    """statcast() for one window with retries on transient errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return statcast(start_dt=start_date, end_dt=end_date)
        except Exception as e:  # noqa: BLE001 - Savant returns varied errors
            msg = str(e)[:120]
            if attempt == MAX_RETRIES:
                print(f"    [FALLO definitivo] {start_date}→{end_date}: {msg}")
                raise
            wait = RETRY_SLEEP * attempt
            print(
                f"    [reintento {attempt}/{MAX_RETRIES}] {start_date}→{end_date} "
                f"falló ({msg}); espero {wait}s"
            )
            time.sleep(wait)


def download_season(year: int, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Download all pitches of a season in windows of CHUNK_DAYS days,
    each with retries, and concatenate them.
    """
    print(f"\n{'=' * 60}")
    print(f"  Descargando temporada {year} ({start_date} → {end_date})")
    print(f"{'=' * 60}")

    start = time.time()
    season_start = datetime.strptime(start_date, "%Y-%m-%d")
    season_end = datetime.strptime(end_date, "%Y-%m-%d")

    frames = []
    window_start = season_start
    while window_start <= season_end:
        window_end = min(window_start + timedelta(days=CHUNK_DAYS - 1), season_end)
        s, e = window_start.strftime("%Y-%m-%d"), window_end.strftime("%Y-%m-%d")
        print(f"  Ventana {s} → {e} ...")
        chunk = _statcast_chunk(s, e)
        if chunk is not None and len(chunk) > 0:
            frames.append(chunk)
            print(f"    {len(chunk):,} pitches")
        window_start = window_end + timedelta(days=1)

    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    elapsed = time.time() - start

    print(f"\nTemporada {year} bajada:")
    print(f"  Pitches: {len(df):,}")
    print(f"  Columnas: {df.shape[1]}")
    print(f"  Tiempo: {elapsed / 60:.1f} minutos")
    if len(df):
        print(f"  Memoria: {df.memory_usage(deep=True).sum() / 1e6:.1f} MB")

    return df


def save_parquet(df: pd.DataFrame, year: int) -> Path:
    """Save the DataFrame as Parquet (compressed columnar format)."""
    path = DATA_DIR / f"statcast_{year}.parquet"
    df.to_parquet(path, compression="snappy", index=False)
    size_mb = path.stat().st_size / 1e6
    print(f"  Guardado en: {path} ({size_mb:.1f} MB)")
    return path


if __name__ == "__main__":
    print("Descargando datos de Statcast (2024-2025)")
    print(f"Datos se guardarán en: {DATA_DIR.absolute()}")

    for year, (start, end) in SEASONS.items():
        out_path = DATA_DIR / f"statcast_{year}.parquet"
        if out_path.exists():
            print(
                f"\n[SKIP] {out_path} ya existe. Bórralo manualmente si quieres re-bajar."
            )
            continue

        df = download_season(year, start, end)
        save_parquet(df, year)

    print("\n" + "=" * 60)
    print("Descarga completa.")
    print("=" * 60)

    # Final summary
    for year in SEASONS:
        path = DATA_DIR / f"statcast_{year}.parquet"
        if path.exists():
            df = pd.read_parquet(path)
            print(f"  {year}: {len(df):>9,} pitches en {path.name}")
