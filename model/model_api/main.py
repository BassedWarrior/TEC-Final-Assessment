import sys
from pathlib import Path


SIM_DIR = Path(__file__).resolve().parent.parent / "simulation"
sys.path.insert(0, str(SIM_DIR))

from predict import simulate_match_from_stats, to_nested  

from fastapi import FastAPI, HTTPException, Query  
from fastapi.middleware.cors import CORSMiddleware 

from schemas import SimulateRequest 

app = FastAPI(
    title="MLB Model API",
    description="Simulación Monte Carlo de partidos a partir de arrays de stats",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/simulate")
def simulate(req: SimulateRequest, nested: bool = Query(False)):
    try:
        out = simulate_match_from_stats(
            home_batters=req.home_batters,
            home_pitcher=req.home_pitcher,
            away_batters=req.away_batters,
            away_pitcher=req.away_pitcher,
            home_bullpen=req.home_bullpen,
            away_bullpen=req.away_bullpen,
            reliever_entry_inning=6,
            n_sims=100,
            seed=42,
            home_team=req.home_team,
            away_team=req.away_team,
        )
    except FileNotFoundError as e:
        # falta pa_model.txt o feature_names.csv
        raise HTTPException(status_code=500, detail=f"Artefacto del modelo no encontrado: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la simulación: {e}")

    return to_nested(out) if nested else out
