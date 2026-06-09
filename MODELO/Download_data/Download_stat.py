import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from pybaseball import statcast


DATA_DIR = Path("../data")
DATA_DIR.mkdir(exist_ok=True)

# Rangos de fechas de temporada regular (aproximados — pybaseball filtra lo real)
SEASONS = {
    2024: ("2024-03-28", "2024-09-29"),
    2025: ("2025-03-27", "2025-09-28"),
}

# Bajamos en ventanas chicas con reintentos. Una sola llamada a statcast() de
# toda la temporada lanza decenas de requests en paralelo; si UNO devuelve un
# mensaje de error (rate-limit), pybaseball revienta toda la descarga. Por
# ventanas, un fallo transitorio solo reintenta esa ventana.
CHUNK_DAYS = 14
MAX_RETRIES = 4
RETRY_SLEEP = 5  # segundos, con backoff lineal


def _statcast_chunk(start_date: str, end_date: str) -> pd.DataFrame:
    """statcast() de una ventana con reintentos ante errores transitorios."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return statcast(start_dt=start_date, end_dt=end_date)
        except Exception as e:  # noqa: BLE001 - Savant devuelve errores variados
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
    Baja todos los pitches de una temporada en ventanas de CHUNK_DAYS días,
    cada una con reintentos, y las concatena.
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
    """Guarda el DataFrame como Parquet (formato columnar, comprimido)."""
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

    # Resumen final
    for year in SEASONS:
        path = DATA_DIR / f"statcast_{year}.parquet"
        if path.exists():
            df = pd.read_parquet(path)
            print(f"  {year}: {len(df):>9,} pitches en {path.name}")
