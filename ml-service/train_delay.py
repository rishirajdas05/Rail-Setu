"""
Train the RailSetu arrival-delay predictor (second model in the ML service).

SYNTHETIC DATA, same as the confirmation model: India does not publish a clean
train-by-train historical delay dataset, so we generate one whose patterns
follow real rules (journey length, number of stops, train class punctuality,
monsoon months, night running) and fit a real regressor. The pipeline is real;
the data is simulated. The API labels every response accordingly.

Run:  python train_delay.py
Out:  model_delay.joblib
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
import joblib

RNG = np.random.default_rng(7)
N = 40_000

TYPES = ["Pass", "Exp", "SF", "MEMU", "Raj", "Shtb", "Drnt", "Mail", "GR"]
TYPE_P = [0.34, 0.24, 0.16, 0.08, 0.03, 0.03, 0.03, 0.03, 0.06]
# minutes added/removed by train class (premium services run tighter)
TYPE_DELAY = {
    "Pass": 14, "MEMU": 3, "Exp": 0, "Mail": 1, "GR": -4,
    "SF": -7, "Raj": -12, "Shtb": -12, "Drnt": -11,
}


def make_dataset(n):
    train_type = RNG.choice(TYPES, size=n, p=TYPE_P)
    journey_hours = np.round(RNG.uniform(1, 38, size=n), 1)
    num_stops = RNG.integers(2, 60, size=n)
    dep_hour = RNG.integers(0, 24, size=n)
    journey_dow = RNG.integers(0, 7, size=n)
    month = RNG.integers(1, 13, size=n)

    tfac = np.array([TYPE_DELAY[t] for t in train_type])
    monsoon = np.isin(month, [6, 7, 8, 9]).astype(float)
    night = ((dep_hour >= 22) | (dep_hour <= 4)).astype(float)

    mean_delay = (
        8.0
        + 1.6 * journey_hours          # delay accumulates over distance/time
        + 0.25 * num_stops             # each halt is a chance to lose time
        + tfac                         # train class punctuality
        + 12.0 * monsoon               # rains
        + 6.0 * night                  # night running / congestion
    )
    # right-skewed noise: most trains near the mean, a tail of big delays
    delay = mean_delay + RNG.gamma(shape=1.6, scale=10.0, size=n) - 12
    delay = np.clip(delay, 0, None)

    return pd.DataFrame({
        "train_type": train_type,
        "journey_hours": journey_hours,
        "num_stops": num_stops,
        "dep_hour": dep_hour,
        "journey_dow": journey_dow,
        "month": month,
        "delay_min": np.round(delay, 0),
    })


def main():
    df = make_dataset(N)
    X = df.drop(columns=["delay_min"])
    y = df["delay_min"]

    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["train_type"]),
        ("num", "passthrough", ["journey_hours", "num_stops", "dep_hour", "journey_dow", "month"]),
    ])
    model = Pipeline([
        ("pre", pre),
        ("reg", GradientBoostingRegressor(random_state=7)),
    ])

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=7)
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)

    print(f"samples     : {N:,}")
    print(f"mean delay  : {y.mean():.1f} min")
    print(f"MAE         : {mean_absolute_error(yte, pred):.1f} min")
    print(f"R^2         : {r2_score(yte, pred):.3f}")

    joblib.dump(model, "model_delay.joblib")
    print("saved -> model_delay.joblib")


if __name__ == "__main__":
    main()