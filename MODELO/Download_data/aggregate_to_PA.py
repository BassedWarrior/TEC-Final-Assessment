from pathlib import Path
 
import pandas as pd
 

DATA_DIR = Path("../data")
SEASONS = [2024, 2025]

PA_OUTCOMES = ["K", "BB", "HBP", "1B", "2B", "3B", "HR", "OUT", "DP", "SF"]

EVENT_MAPPING = {
    # Strikeouts
    "strikeout":                    "K",
    "strikeout_double_play":        "K",

    # Walks
    "walk":                         "BB",
    "intent_walk":                  "BB",
    "catcher_interf":               "BB",

    # HBP
    "hit_by_pitch":                 "HBP",

    # Hits
    "single":                       "1B",
    "double":                       "2B",
    "triple":                       "3B",
    "home_run":                     "HR",


    "field_error":                  "1B",

    # Out genérico (1 out, el bateador es eliminado)
    "field_out":                    "OUT",
    "force_out":                    "OUT",
    "fielders_choice":              "OUT",
    "fielders_choice_out":          "OUT",
    "sac_bunt":                     "OUT",
    "sac_bunt_double_play":         "OUT",
    "other_out":                    "OUT",
    "batter_interference":          "OUT",  # raro

    # Double play (2 outs). Triple play se pliega aquí (≈2 casos/temporada).
    "grounded_into_double_play":    "DP",
    "double_play":                  "DP",
    "triple_play":                  "DP",

    # Sac fly (1 out + anota el corredor de 3B)
    "sac_fly":                      "SF",
    "sac_fly_double_play":          "SF",
}


EVENTS_TO_DROP = {
    "truncated_pa",
    "game_advisory",
    "wild_pitch",      
    "passed_ball",     
    "stolen_base_2b",
    "stolen_base_3b",
    "stolen_base_home",
    "caught_stealing_2b",
    "caught_stealing_3b",
    "caught_stealing_home",
    "pickoff_1b",
    "pickoff_2b",
    "pickoff_3b",
    "pickoff_caught_stealing_2b",
    "pickoff_caught_stealing_3b",
    "pickoff_caught_stealing_home",
    "balk",
    "runner_double_play",
}

PA_LEVEL_COLUMNS = [
    "game_pk",
    "game_date",
    "at_bat_number",
    "pitcher",
    "batter",
    "p_throws",        # mano del pitcher (L/R)
    "stand",           # mano del bateador (L/R)
    "inning",
    "inning_topbot",
    "outs_when_up",
    "on_1b",           # ID del runner en 1B (NaN si vacío)
    "on_2b",
    "on_3b",
    "bat_score",
    "fld_score",
    "home_team",
    "away_team",
    "events",          # outcome original (lo renombramos a events_original)
]


def load_statcast(year: int) -> pd.DataFrame:
    path=DATA_DIR/f"statcast_{year}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"No encontré {path}. Corre 01_download_statcast.py primero."
        )
    print(f" Cargando {path.name}...")
    df=pd.read_parquet(path)
    print(f" {len(df):,} pitches, {df.shape[1]} columnas")
    return df

def collapse_to_pa(pitches: pd.DataFrame) -> pd.DataFrame:
    last_pitches= pitches[pitches["events"].notna()].copy()
    
    # Defensa: cada (game_pk, at_bat_number) debería aparecer una sola vez aquí.
    # Si aparece más de una, hay un dato raro — nos quedamos con el último.
    
    last_pitches = last_pitches.sort_values(
        ["game_pk", "at_bat_number"]
    ).drop_duplicates(subset=["game_pk", "at_bat_number"], keep="last")
    
    # Nos quedamos solo con las columnas que necesitamos a nivel PA
    
    available_cols=[c for c in PA_LEVEL_COLUMNS if c in last_pitches.columns]
    pa= last_pitches[available_cols].copy()
    pa=pa.rename(columns={"events": "events_original"})
    
    return pa


def add_pa_outcome(pa: pd.DataFrame) -> pd.DataFrame:
    
    n_before= len(pa)
    pa=pa[~pa["events_original"].isin(EVENTS_TO_DROP)].copy()
    n_dropped_drop_list = n_before - len(pa)
    
    # Mapear los eventos a las 8 clases
    pa["pa_outcome"] = pa["events_original"].map(EVENT_MAPPING)
    
    # Reportar eventos no mapeados (deberían ser pocos o ninguno)
    unmapped = pa[pa["pa_outcome"].isna()]
    if len(unmapped) > 0:
        print(f"\n  {len(unmapped)} PAs con events no mapeados:")
        print(unmapped["events_original"].value_counts().head(10))
        # Los descartamos para no contaminar
        pa = pa[pa["pa_outcome"].notna()].copy()
        
    return pa, n_dropped_drop_list

def add_runner_booleans(pa: pd.DataFrame) -> pd.DataFrame:
    """Convierte on_1b/on_2b/on_3b de IDs (o NaN) a booleanos."""
    for base in ["on_1b", "on_2b", "on_3b"]:
        if base in pa.columns:
            pa[base] = pa[base].notna()
    return pa

def report_distribution(pa: pd.DataFrame, year: int) -> None:
    """Reporta la distribución de outcomes y la compara con liga promedio."""
    print(f"\n  Distribución de outcomes en {year}:")
    print(f"  {'Clase':<6} {'Conteo':>10} {'%':>8}    {'Liga 2024':>10}")
    print(f"  {'-' * 50}")
 
    # Benchmarks de liga (de simulator.py)
    league_avg = {
        "K":   0.226, "BB":  0.082, "HBP": 0.012, "1B":  0.141,
        "2B":  0.044, "3B":  0.004, "HR":  0.029, "OUT": 0.429,
        "DP":  0.020, "SF":  0.007,
    }
 
    counts = pa["pa_outcome"].value_counts()
    total = len(pa)
    for outcome in PA_OUTCOMES:
        n = counts.get(outcome, 0)
        pct = n / total
        bench = league_avg[outcome]
        delta = pct - bench
        marker = " ✓" if abs(delta) < 0.01 else f"  ({delta:+.3f})"
        print(f"  {outcome:<6} {n:>10,} {pct*100:>7.2f}%   {bench*100:>8.2f}%{marker}")
    print(f"  {'-' * 50}")
    print(f"  {'TOTAL':<6} {total:>10,}")
    
    
if __name__ == "__main__":
    print("=" * 60)
    print("Agregando pitches a plate appearances")
    print("=" * 60)
 
    for year in SEASONS:
        out_path = DATA_DIR / f"pa_{year}.parquet"
        if out_path.exists():
            print(f"\n[SKIP] {out_path.name} ya existe. Bórralo para regenerar.")
            continue
 
        print(f"\n--- Temporada {year} ---")
        pitches = load_statcast(year)
 
        print(f"  Colapsando a PAs...")
        pa = collapse_to_pa(pitches)
        print(f"    {len(pa):,} PAs identificados")
 
        print(f"  Mapeando outcomes a 8 clases...")
        pa, n_dropped = add_pa_outcome(pa)
        if n_dropped > 0:
            print(f"    Descartados {n_dropped:,} eventos no-PA (steals, balks, etc.)")
 
        print(f"  Convirtiendo runners a booleanos...")
        pa = add_runner_booleans(pa)
 
        report_distribution(pa, year)
 
        # Guardar
        pa.to_parquet(out_path, compression="snappy", index=False)
        size_mb = out_path.stat().st_size / 1e6
        print(f"\n  Guardado en {out_path.name} ({size_mb:.1f} MB)")
 
    print("\n" + "=" * 60)
    print("Agregación completa.")
    print("=" * 60)