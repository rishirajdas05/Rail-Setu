"""
RailSetu ML service — waitlist confirmation predictor (FastAPI).

Serves the model trained by train.py. NOTE: the model is trained on SYNTHETIC
data (see train.py); its probabilities demonstrate the pipeline, not real
railway records.

Run:  uvicorn app:app --reload --port 8001
Docs: http://127.0.0.1:8001/docs
"""

from datetime import date
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

MODEL_PATH = Path(__file__).parent / "model.joblib"
DELAY_MODEL_PATH = Path(__file__).parent / "model_delay.joblib"
RANK_MODEL_PATH = Path(__file__).parent / "model_rank.joblib"
CLASSES = {"1A", "2A", "3A", "SL", "CC", "2S"}
QUOTAS = {"GN", "TQ", "LD", "SS"}

app = FastAPI(title="RailSetu ML Service", version="1.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None
delay_model = joblib.load(DELAY_MODEL_PATH) if DELAY_MODEL_PATH.exists() else None
rank_model = joblib.load(RANK_MODEL_PATH) if RANK_MODEL_PATH.exists() else None


class PredictIn(BaseModel):
    travel_class: str = Field(..., examples=["SL"])
    quota: str = Field("GN", examples=["GN"])
    waitlist_position: int = Field(..., ge=1, le=500, examples=[22])
    journey_date: Optional[str] = Field(None, examples=["2026-07-01"])  # YYYY-MM-DD
    days_to_journey: Optional[int] = Field(None, ge=0, le=120)
    journey_dow: Optional[int] = Field(None, ge=0, le=6)  # 0=Mon


def _derive(inp: PredictIn):
    days = inp.days_to_journey
    dow = inp.journey_dow
    if inp.journey_date:
        try:
            d = date.fromisoformat(inp.journey_date)
        except ValueError:
            raise HTTPException(400, "journey_date must be YYYY-MM-DD.")
        if days is None:
            days = max(0, min(120, (d - date.today()).days))
        if dow is None:
            dow = d.weekday()
    if days is None:
        days = 30
    if dow is None:
        dow = 0
    return days, dow


def _band(p: float):
    if p >= 0.70:
        return "High"
    if p >= 0.40:
        return "Moderate"
    return "Low"


class DelayIn(BaseModel):
    train_type: str = Field("Exp", examples=["SF"])
    journey_hours: float = Field(..., ge=0, le=60, examples=[20.5])
    num_stops: int = Field(..., ge=1, le=200, examples=[30])
    dep_hour: int = Field(12, ge=0, le=23, examples=[22])
    journey_dow: int = Field(0, ge=0, le=6)
    month: int = Field(1, ge=1, le=12, examples=[7])


def _delay_band(mins: float):
    if mins < 15:
        return "Likely on time"
    if mins < 60:
        return "Minor delay"
    return "Major delay"


class RankItem(BaseModel):
    train_number: str = Field(..., examples=["12626"])
    train_type: str = Field("Exp", examples=["SF"])
    journey_hours: float = Field(..., ge=0.1, le=60, examples=[12.5])
    dep_hour: int = Field(12, ge=0, le=23)
    fare: Optional[float] = Field(None, ge=0, examples=[1395])


class RankIn(BaseModel):
    items: list[RankItem]


def _rank_band(s: float):
    if s >= 70:
        return "Great match"
    if s >= 50:
        return "Good match"
    return "Fair match"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "confirmation_model": model is not None,
        "delay_model": delay_model is not None,
        "rank_model": rank_model is not None,
    }


@app.post("/predict/rank")
def predict_rank(inp: RankIn):
    if rank_model is None:
        raise HTTPException(503, "Rank model not loaded. Run train_rank.py first.")
    if not inp.items:
        return {"results": [], "model": "synthetic-rank-v1"}

    rows = []
    for it in inp.items:
        hours = max(it.journey_hours, 0.1)
        fph = (it.fare / hours) if (it.fare and it.fare > 0) else 120.0
        rows.append({
            "train_type": it.train_type,
            "journey_hours": hours,
            "dep_hour": it.dep_hour,
            "fare_per_hour": fph,
        })
    scores = rank_model.predict(pd.DataFrame(rows))

    results = [{
        "train_number": it.train_number,
        "score": int(max(0, min(100, round(float(s))))),
        "band": _rank_band(float(s)),
    } for it, s in zip(inp.items, scores)]
    results.sort(key=lambda r: r["score"], reverse=True)

    return {
        "results": results,
        "model": "synthetic-rank-v1",
        "disclaimer": "Trained on synthetic data; for demonstration only.",
    }


@app.post("/predict/confirmation")
def predict_confirmation(inp: PredictIn):
    if model is None:
        raise HTTPException(503, "Model not loaded. Run train.py first.")
    if inp.travel_class not in CLASSES:
        raise HTTPException(400, f"Unknown travel_class. Use one of {sorted(CLASSES)}.")
    if inp.quota not in QUOTAS:
        raise HTTPException(400, f"Unknown quota. Use one of {sorted(QUOTAS)}.")

    days, dow = _derive(inp)
    row = pd.DataFrame([{
        "travel_class": inp.travel_class,
        "quota": inp.quota,
        "waitlist_position": inp.waitlist_position,
        "days_to_journey": days,
        "journey_dow": dow,
    }])
    prob = float(model.predict_proba(row)[0, 1])

    return {
        "confirmation_probability": round(prob, 3),
        "percent": round(prob * 100),
        "band": _band(prob),
        "prediction": "likely to confirm" if prob >= 0.5 else "unlikely to confirm",
        "inputs": {
            "travel_class": inp.travel_class,
            "quota": inp.quota,
            "waitlist_position": inp.waitlist_position,
            "days_to_journey": days,
            "journey_dow": dow,
        },
        "model": "synthetic-gbdt-v1",
        "disclaimer": "Trained on synthetic data; for demonstration only.",
    }


@app.post("/predict/delay")
def predict_delay(inp: DelayIn):
    if delay_model is None:
        raise HTTPException(503, "Delay model not loaded. Run train_delay.py first.")

    row = pd.DataFrame([{
        "train_type": inp.train_type,
        "journey_hours": inp.journey_hours,
        "num_stops": inp.num_stops,
        "dep_hour": inp.dep_hour,
        "journey_dow": inp.journey_dow,
        "month": inp.month,
    }])
    mins = float(delay_model.predict(row)[0])
    mins = max(0.0, mins)

    return {
        "predicted_delay_min": round(mins),
        "band": _delay_band(mins),
        "range_min": [max(0, round(mins - 12)), round(mins + 18)],
        "inputs": inp.model_dump(),
        "model": "synthetic-gbr-v1",
        "disclaimer": "Trained on synthetic data; for demonstration only.",
    }