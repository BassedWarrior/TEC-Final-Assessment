from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
 
import numpy as np
import pandas as pd
import lightgbm as lgb

from GameState import GameState, Outcome


DATA_DIR = Path("./data")
MODELS_DIR = Path("./models")
 
# Orden de las clases (debe matchear el modelo entrenado)
OUTCOME_ORDER = ["K", "BB", "HBP", "1B", "2B", "3B", "HR", "OUT"]
OUTCOME_FROM_INDEX = {
    0: Outcome.STRIKEOUT,
    1: Outcome.WALK,
    2: Outcome.HIT_BY_PITCH,
    3: Outcome.SINGLE,
    4: Outcome.DOUBLE,
    5: Outcome.TRIPLE,
    6: Outcome.HOME_RUN,
    7: Outcome.OUT_IN_PLAY,
}

LEAGUE_AVG = {
    "avg":     0.243, "obp":     0.312, "slg":     0.399, "iso":     0.156,
    "k_rate":  0.226, "bb_rate": 0.082, "hr_rate": 0.029,
}

@dataclass
class BatterProfile:
    """Stats de un bateador (las features que espera el modelo)."""
    batter_id: int
    stand: str  # "L", "R", o "S"
    pa_count: float
    avg: float
    obp: float
    slg: float
    iso: float
    k_rate: float
    bb_rate: float
    hr_rate: float
    is_rookie: bool = False
 
 
@dataclass
class PitcherProfile:
    """Stats de un pitcher (las features que espera el modelo)."""
    pitcher_id: int
    throws: str  # "L" o "R"
    pa_count: float
    avg: float
    obp: float
    slg: float
    iso: float
    k_rate: float
    bb_rate: float
    hr_rate: float
    is_new: bool = False
 
 
@dataclass
class TeamLineup:
    team_name: str
    batters: list[BatterProfile]  # exactamente 9
    pitcher: PitcherProfile
 
    def __post_init__(self):
        if len(self.batters) != 9:
            raise ValueError(f"Lineup necesita 9 bateadores, tiene {len(self.batters)}")
 
    def batter_at(self, idx: int) -> BatterProfile:
        return self.batters[idx]
    
def build_player_profiles(pa_2024: pd.DataFrame) -> tuple[dict, dict]:
    
    # Bateadores
    df = pa_2024.copy()
    df["is_hit"] = df["pa_outcome"].isin(["1B", "2B", "3B", "HR"]).astype(int)
    df["is_K"]   = (df["pa_outcome"] == "K").astype(int)
    df["is_BB"]  = (df["pa_outcome"] == "BB").astype(int)
    df["is_HBP"] = (df["pa_outcome"] == "HBP").astype(int)
    df["is_HR"]  = (df["pa_outcome"] == "HR").astype(int)
    df["total_bases"] = (
        (df["pa_outcome"] == "1B").astype(int) +
        2 * (df["pa_outcome"] == "2B").astype(int) +
        3 * (df["pa_outcome"] == "3B").astype(int) +
        4 * df["is_HR"]
    )
 
    batter_profiles = {}
    for batter_id, group in df.groupby("batter"):
        pa_count = len(group)
        at_bats = max(pa_count - group["is_BB"].sum() - group["is_HBP"].sum(), 1)
        hits = group["is_hit"].sum()
 
        # Mano: tomamos el modo (la mano más común con la que bateó)
        stand = group["stand"].mode().iloc[0] if not group["stand"].mode().empty else "R"
 
        batter_profiles[batter_id] = BatterProfile(
            batter_id=batter_id,
            stand=stand,
            pa_count=pa_count,
            avg=hits / at_bats,
            obp=(hits + group["is_BB"].sum() + group["is_HBP"].sum()) / pa_count,
            slg=group["total_bases"].sum() / at_bats,
            iso=(group["total_bases"].sum() / at_bats) - (hits / at_bats),
            k_rate=group["is_K"].sum() / pa_count,
            bb_rate=group["is_BB"].sum() / pa_count,
            hr_rate=group["is_HR"].sum() / pa_count,
            is_rookie=False,
        )
 
    # Pitchers (misma lógica, agrupado por pitcher)
    pitcher_profiles = {}
    for pitcher_id, group in df.groupby("pitcher"):
        pa_count = len(group)
        at_bats = max(pa_count - group["is_BB"].sum() - group["is_HBP"].sum(), 1)
        hits = group["is_hit"].sum()
 
        throws = group["p_throws"].mode().iloc[0] if not group["p_throws"].mode().empty else "R"
 
        pitcher_profiles[pitcher_id] = PitcherProfile(
            pitcher_id=pitcher_id,
            throws=throws,
            pa_count=pa_count,
            avg=hits / at_bats,
            obp=(hits + group["is_BB"].sum() + group["is_HBP"].sum()) / pa_count,
            slg=group["total_bases"].sum() / at_bats,
            iso=(group["total_bases"].sum() / at_bats) - (hits / at_bats),
            k_rate=group["is_K"].sum() / pa_count,
            bb_rate=group["is_BB"].sum() / pa_count,
            hr_rate=group["is_HR"].sum() / pa_count,
            is_new=False,
        )
 
    return batter_profiles, pitcher_profiles
 
 
def make_league_avg_batter(batter_id: int = -1, stand: str = "R") -> BatterProfile:
    """Bateador 'promedio de liga' para rookies."""
    return BatterProfile(
        batter_id=batter_id, stand=stand, pa_count=0,
        avg=LEAGUE_AVG["avg"], obp=LEAGUE_AVG["obp"], slg=LEAGUE_AVG["slg"],
        iso=LEAGUE_AVG["iso"], k_rate=LEAGUE_AVG["k_rate"],
        bb_rate=LEAGUE_AVG["bb_rate"], hr_rate=LEAGUE_AVG["hr_rate"],
        is_rookie=True,
    )
 
 
def make_league_avg_pitcher(pitcher_id: int = -1, throws: str = "R") -> PitcherProfile:
    """Pitcher 'promedio de liga' para nuevos."""
    return PitcherProfile(
        pitcher_id=pitcher_id, throws=throws, pa_count=0,
        avg=LEAGUE_AVG["avg"], obp=LEAGUE_AVG["obp"], slg=LEAGUE_AVG["slg"],
        iso=LEAGUE_AVG["iso"], k_rate=LEAGUE_AVG["k_rate"],
        bb_rate=LEAGUE_AVG["bb_rate"], hr_rate=LEAGUE_AVG["hr_rate"],
        is_new=True,
    )
 

class ModelSampler:
    
 
    def __init__(
        self,
        model_path: Path,
        feature_names: list[str],
        home_lineup: TeamLineup,
        away_lineup: TeamLineup,
        seed: Optional[int] = None,
    ):
        self.model = lgb.Booster(model_file=str(model_path))
        self.feature_names = feature_names
        self.home_lineup = home_lineup
        self.away_lineup = away_lineup
        self.rng = np.random.default_rng(seed)
 
    def _build_feature_vector(self, state: GameState) -> np.ndarray:
        
        # Identificar quién batea y quién pitcha
        if state.is_top:
            # Top inning: batea el visitante, pitcha el local
            batter = self.away_lineup.batter_at(state.away_batter_idx)
            pitcher = self.home_lineup.pitcher
        else:
            # Bottom inning: batea el local, pitcha el visitante
            batter = self.home_lineup.batter_at(state.home_batter_idx)
            pitcher = self.away_lineup.pitcher
 

        # Bases state: bit 0=1B, bit 1=2B, bit 2=3B
        on1b, on2b, on3b = state.bases
        bases_state = int(on1b) + int(on2b) * 2 + int(on3b) * 4
 
        # Score diff (desde la perspectiva del bateador)
        if state.is_top:
            # Bateador = away
            score_diff = state.away_score - state.home_score
        else:
            score_diff = state.home_score - state.away_score
 
        # Same-handed matchup
        same_handed = int(
            (batter.stand == "R" and pitcher.throws == "R") or
            (batter.stand == "L" and pitcher.throws == "L")
        )
 
        # --- Diccionario de todas las features ---
        # ¡El nombre de cada feature debe matchear feature_names.csv!
        features = {
            # Manos
            "p_throws_R":     int(pitcher.throws == "R"),
            "stand_R":        int(batter.stand == "R"),
            "stand_S":        int(batter.stand == "S"),
            "same_handed":    same_handed,
            # Game state
            "inning":         state.inning,
            "is_top":         int(state.is_top),
            "outs_when_up":   state.outs,
            "bases_state":    bases_state,
            "score_diff":     score_diff,
            # Bateador
            "b_pa_count":     batter.pa_count,
            "b_avg":          batter.avg,
            "b_obp":          batter.obp,
            "b_slg":          batter.slg,
            "b_iso":          batter.iso,
            "b_k_rate":       batter.k_rate,
            "b_bb_rate":      batter.bb_rate,
            "b_hr_rate":      batter.hr_rate,
            "b_is_rookie":    int(batter.is_rookie),
            # Pitcher
            "p_pa_count":     pitcher.pa_count,
            "p_avg":          pitcher.avg,
            "p_obp":          pitcher.obp,
            "p_slg":          pitcher.slg,
            "p_iso":          pitcher.iso,
            "p_k_rate":       pitcher.k_rate,
            "p_bb_rate":      pitcher.bb_rate,
            "p_hr_rate":      pitcher.hr_rate,
            "p_is_new":       int(pitcher.is_new),
        }
 
        # Construir vector en el orden correcto (el orden de feature_names)
        vec = np.array([features[name] for name in self.feature_names], dtype=np.float64)
        return vec.reshape(1, -1)  # 2D para LightGBM
 
    def __call__(self, state: GameState) -> Outcome:
        """
        Predice la distribución sobre outcomes y samplea uno.
        Esta es la interfaz que play_game llama en cada PA.
        """
        x = self._build_feature_vector(state)
        # predict() de LightGBM en multiclase devuelve (n_samples, n_classes)
        probs = self.model.predict(x)[0]  # vector de 8 probabilidades
 
        # Muestreo según la distribución predicha
        outcome_idx = self.rng.choice(len(probs), p=probs)
        return OUTCOME_FROM_INDEX[outcome_idx]
 
 

def build_lineup_from_ids(
    team_name: str,
    batter_ids: list[int],
    pitcher_id: int,
    batter_profiles: dict,
    pitcher_profiles: dict,
) -> TeamLineup:
    """
    Construye un TeamLineup buscando los profiles por ID.
    Si algún ID no existe en los profiles (rookie), usa promedio de liga.
    """
    if len(batter_ids) != 9:
        raise ValueError(f"Necesito 9 batter_ids, recibí {len(batter_ids)}")
 
    batters = []
    for bid in batter_ids:
        if bid in batter_profiles:
            batters.append(batter_profiles[bid])
        else:
            print(f"  batter_id {bid} no encontrado, usando promedio de liga")
            batters.append(make_league_avg_batter(bid))
 
    if pitcher_id in pitcher_profiles:
        pitcher = pitcher_profiles[pitcher_id]
    else:
        print(f"    pitcher_id {pitcher_id} no encontrado, usando promedio de liga")
        pitcher = make_league_avg_pitcher(pitcher_id)
 
    return TeamLineup(team_name=team_name, batters=batters, pitcher=pitcher)

# ---------------------------------------------------------------------------
# Diagnostic tests: validar que el modelo se comporta lógicamente
# ---------------------------------------------------------------------------
def simulate_matchup(
    model_path: Path,
    feature_names: list,
    home_lineup: TeamLineup,
    away_lineup: TeamLineup,
    n_games: int = 500,
    seed: int = 42,
) -> dict:
    """
    Simula n_games juegos entre dos lineups dados y devuelve stats agregadas.
    """
    from Simulador import play_game

    sampler = ModelSampler(
        model_path=model_path,
        feature_names=feature_names,
        home_lineup=home_lineup,
        away_lineup=away_lineup,
        seed=seed,
    )
    results = [play_game(sampler) for _ in range(n_games)]

    return {
        "home_runs_avg": np.mean([r.home_score for r in results]),
        "away_runs_avg": np.mean([r.away_score for r in results]),
        "home_runs_std": np.std([r.home_score for r in results]),
        "away_runs_std": np.std([r.away_score for r in results]),
        "home_win_pct":  np.mean([r.home_won for r in results]),
        "combined_avg":  np.mean([r.home_score + r.away_score for r in results]),
    }


def run_diagnostic_tests(
    model_path: Path,
    feature_names: list,
    batter_profiles: dict,
    pitcher_profiles: dict,
):
    """
    Tres tests diagnósticos para validar que el modelo se comporta
    correctamente en distintos escenarios.
    """
    print("\n" + "=" * 70)
    print("TESTS DIAGNÓSTICOS")
    print("=" * 70)

    # Preparar listas ordenadas de jugadores
    all_batters_sorted = sorted(
        batter_profiles.values(), key=lambda b: b.slg, reverse=True
    )
    all_pitchers_sorted = sorted(
        pitcher_profiles.values(), key=lambda p: p.k_rate, reverse=True
    )

    # Necesitamos pitchers con suficientes PAs para ser representativos
    qualified_pitchers = [p for p in all_pitchers_sorted if p.pa_count >= 300]
    qualified_batters  = [b for b in all_batters_sorted if b.pa_count >= 300]

    # Pitcher promedio: el de la mediana
    avg_pitcher = qualified_pitchers[len(qualified_pitchers) // 2]
    print(f"\nPitcher de referencia (mediana): K%={avg_pitcher.k_rate:.3f}, "
          f"AVG-contra={avg_pitcher.avg:.3f}")

    # =====================================================================
    # TEST 1: Lineups simétricos (sanity check)
    # =====================================================================
    print("\n" + "-" * 70)
    print("[TEST 1] Lineups simétricos: jugadores promedio en ambos equipos")
    print("-" * 70)
    print("Expectativa: runs HOME ≈ runs AWAY, win% ≈ 50%, runs combinados ≈ 8.8")

    # Tomamos 18 bateadores cerca de la mediana
    mid = len(qualified_batters) // 2
    median_batters = qualified_batters[mid - 9 : mid + 9]

    home_sym = TeamLineup(team_name="HOME-SYM", batters=median_batters[:9], pitcher=avg_pitcher)
    away_sym = TeamLineup(team_name="AWAY-SYM", batters=median_batters[9:18], pitcher=avg_pitcher)

    stats = simulate_matchup(model_path, feature_names, home_sym, away_sym, n_games=500)
    print(f"\n  Runs HOME / juego:   {stats['home_runs_avg']:.2f}")
    print(f"  Runs AWAY / juego:   {stats['away_runs_avg']:.2f}")
    print(f"  Diferencia:          {stats['home_runs_avg'] - stats['away_runs_avg']:+.2f}")
    print(f"  Runs combinados:     {stats['combined_avg']:.2f}  (MLB real: ~8.8)")
    print(f"  HOME win pct:        {stats['home_win_pct']*100:.1f}%  (esperado: ~50%)")

    # Diagnóstico
    diff = abs(stats['home_runs_avg'] - stats['away_runs_avg'])
    if diff < 0.3 and abs(stats['home_win_pct'] - 0.5) < 0.05:
        print("  ✓ El modelo es simétrico: lineups iguales producen resultados similares")
    else:
        print("  ⚠️  Asimetría inesperada — investigar")

    # =====================================================================
    # TEST 2: Lineups invertidos (confirmar asimetría viene de inputs)
    # =====================================================================
    print("\n" + "-" * 70)
    print("[TEST 2] Lineups invertidos: top 9 en AWAY, siguientes 9 en HOME")
    print("-" * 70)
    print("Expectativa: AWAY produce más runs, HOME win% ~40%")

    top_18 = qualified_batters[:18]
    home_inv = TeamLineup(team_name="HOME-INV", batters=top_18[9:18], pitcher=avg_pitcher)
    away_inv = TeamLineup(team_name="AWAY-INV", batters=top_18[:9], pitcher=avg_pitcher)

    stats = simulate_matchup(model_path, feature_names, home_inv, away_inv, n_games=500)
    print(f"\n  Runs HOME / juego:   {stats['home_runs_avg']:.2f}  (lineup #10-18)")
    print(f"  Runs AWAY / juego:   {stats['away_runs_avg']:.2f}  (lineup #1-9)")
    print(f"  Diferencia AWAY−HOME: {stats['away_runs_avg'] - stats['home_runs_avg']:+.2f}")
    print(f"  HOME win pct:        {stats['home_win_pct']*100:.1f}%  (esperado: ~40%)")

    if stats['away_runs_avg'] > stats['home_runs_avg'] and stats['home_win_pct'] < 0.5:
        print("  ✓ La asimetría sigue al lineup, no a un sesgo del modelo")
    else:
        print("  ⚠️  Patrón inesperado — posible bug en home/away handling")

    # =====================================================================
    # TEST 3: Matchup extremo (elite vs malo)
    # =====================================================================
    print("\n" + "-" * 70)
    print("[TEST 3] Matchup extremo: top 9 bateadores vs lineup débil")
    print("-" * 70)
    print("Expectativa: diferencia GRANDE en runs entre los dos equipos")

    top_9       = qualified_batters[:9]
    bottom_9    = qualified_batters[-9:]  # los 9 con SLG más bajo
    elite_pitcher = qualified_pitchers[0]  # el de mayor K%
    bad_pitcher   = qualified_pitchers[-1]  # el de menor K%

    print(f"\n  Elite pitcher: K%={elite_pitcher.k_rate:.3f}")
    print(f"  Bad pitcher:   K%={bad_pitcher.k_rate:.3f}")
    print(f"  Top batters SLG promedio:    {np.mean([b.slg for b in top_9]):.3f}")
    print(f"  Bottom batters SLG promedio: {np.mean([b.slg for b in bottom_9]):.3f}")

    home_extreme = TeamLineup(team_name="HOME-ELITE", batters=top_9, pitcher=elite_pitcher)
    away_extreme = TeamLineup(team_name="AWAY-BAD",   batters=bottom_9, pitcher=bad_pitcher)

    stats = simulate_matchup(model_path, feature_names, home_extreme, away_extreme, n_games=500)
    print(f"\n  Runs HOME (elite vs bad pitcher):  {stats['home_runs_avg']:.2f}")
    print(f"  Runs AWAY (weak vs elite pitcher): {stats['away_runs_avg']:.2f}")
    print(f"  Diferencia:                        {stats['home_runs_avg'] - stats['away_runs_avg']:+.2f}")
    print(f"  HOME win pct:                      {stats['home_win_pct']*100:.1f}%")

    if stats['home_runs_avg'] - stats['away_runs_avg'] > 2.0 and stats['home_win_pct'] > 0.70:
        print("  ✓ El modelo distingue dramáticamente entre matchups extremos")
    elif stats['home_runs_avg'] - stats['away_runs_avg'] > 1.0:
        print("  ~ Diferencia moderada (esperaríamos más en el caso extremo)")
    else:
        print("  ⚠️  El modelo NO está distinguiendo matchups extremos lo suficiente")

    print("\n" + "=" * 70)
    
    
if __name__ == "__main__":
    print("=" * 60)
    print("Cargando modelo y construyendo profiles...")
    print("=" * 60)
 
    # Cargar modelo y feature names
    model_path = MODELS_DIR / "pa_model.txt"
    if not model_path.exists():
        raise FileNotFoundError(
            f"No encontré {model_path}. Corre 05_train_model.py primero."
        )
 
    feature_names = pd.read_csv(
        DATA_DIR / "feature_names.csv", header=None
    )[0].tolist()
    print(f"  Modelo: {model_path}")
    print(f"  Features: {len(feature_names)}")
 
    # Construir profiles desde 2024
    print("\n  Construyendo profiles de jugadores...")
    pa_2024 = pd.read_parquet(DATA_DIR / "pa_2024.parquet")
    batter_profiles, pitcher_profiles = build_player_profiles(pa_2024)
    print(f"  {len(batter_profiles):,} bateadores, {len(pitcher_profiles):,} pitchers")
 
    # Demo: tomar los top 9 bateadores y top pitcher por PAs como prueba
    print("\n  Construyendo lineup de prueba con top jugadores...")
    top_batters = sorted(
        batter_profiles.values(), key=lambda b: b.pa_count, reverse=True
    )[:18]  # top 18 → 9 para cada equipo
    top_pitchers = sorted(
        pitcher_profiles.values(), key=lambda p: p.pa_count, reverse=True
    )[:2]
 
    home_lineup = TeamLineup(
        team_name="HOME",
        batters=top_batters[:9],
        pitcher=top_pitchers[0],
    )
    away_lineup = TeamLineup(
        team_name="AWAY",
        batters=top_batters[9:18],
        pitcher=top_pitchers[1],
    )
 
    print(f"  HOME pitcher: {home_lineup.pitcher.pitcher_id} "
          f"(K%={home_lineup.pitcher.k_rate:.3f})")
    print(f"  AWAY pitcher: {away_lineup.pitcher.pitcher_id} "
          f"(K%={away_lineup.pitcher.k_rate:.3f})")
 
    # Construir sampler
    print("\n  Construyendo ModelSampler...")
    sampler = ModelSampler(
        model_path=model_path,
        feature_names=feature_names,
        home_lineup=home_lineup,
        away_lineup=away_lineup,
        seed=42,
    )
 
    # Simular un solo juego con detalle
    print("\n" + "=" * 60)
    print("Simulando 1 juego con el modelo...")
    print("=" * 60)
 
    from Simulador import play_game
    result = play_game(sampler)
    print(f"\n  Score final: HOME {result.home_score} - AWAY {result.away_score}")
    print(f"  PAs jugados: {result.total_pas}")
    print(f"  Innings:     {result.innings_played}")
    print(f"  Hits H-A:    {result.home_hits}-{result.away_hits}")
 
    # Simular 1000 juegos para sanity check rápido
    print("\n  Simulando 1000 juegos para validación rápida...")
    sampler_for_loop = ModelSampler(
        model_path=model_path, feature_names=feature_names,
        home_lineup=home_lineup, away_lineup=away_lineup, seed=42,
    )
    results = [play_game(sampler_for_loop) for _ in range(1000)]
    home_runs_avg = np.mean([r.home_score for r in results])
    away_runs_avg = np.mean([r.away_score for r in results])
    home_wins_pct = np.mean([r.home_won for r in results])
    print(f"\n  Promedios sobre 1000 juegos:")
    print(f"    Runs HOME / juego:  {home_runs_avg:.2f}")
    print(f"    Runs AWAY / juego:  {away_runs_avg:.2f}")
    print(f"    HOME win pct:       {home_wins_pct*100:.1f}%")
    
    run_diagnostic_tests(
        model_path=model_path,
        feature_names=feature_names,
        batter_profiles=batter_profiles,
        pitcher_profiles=pitcher_profiles,
    )
 