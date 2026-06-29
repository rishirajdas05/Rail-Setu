"""
Train the RailSetu "Recommended" ranker.

This is a pointwise learning-to-rank model: it learns a 0-100 desirability
("match") score for a train on a route, so search results can be ordered by
overall quality rather than a single column. It combines what a traveller
actually trades off: journey time, the train's typical punctuality/comfort
(via type), how convenient the departure hour is, and value for money
(fare per hour).

IMPORTANT: like the other RailSetu models this is trained on SYNTHETIC data.
Indian Railways publishes no labelled "desirability" outcomes, so we generate a
dataset from sensible domain rules and train a genuine scikit-learn pipeline on
it. The pipeline (feature engineering -> training -> serialization -> serving)
is real; only the labels are simulated.

Run:  python train_rank.py
Out:  model_rank.joblib
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

RNG = np.random.default_rng(11)
N = 40_000

TYPES = ["Raj", "Shtb", "Drnt", "GR", "SF", "Exp", "Mail", "SKr", "Hyd", "Pass", "MEMU"]
TYPE_P = [0.04, 0.04, 0.03, 0.04, 0.20, 0.26, 0.12, 0.05, 0.05, 0.10, 0.07]

# Comfort / punctuality bonus by type (premium trains score higher).
TYPE_QUALITY = {
    "Raj": 20, "Shtb": 20, "Drnt": 17, "GR": 14, "SF": 10,
    "Exp": 2, "Mail": 1, "SKr": 6, "Hyd": 5, "Pass": -10, "MEMU": -8,
}


def _dep_convenience(dep_hour):
    # Morning (6-10) and evening (16-21) are most convenient; late night worst.
    conv = np.full(dep_hour.shape, 3.0)
    conv[(dep_hour >= 6) & (dep_hour <= 10)] = 9.0
    conv[(dep_hour >= 16) & (dep_hour <= 21)] = 8.0
    conv[(dep_hour >= 22) | (dep_hour <= 4)] = -7.0
    return conv


def make_dataset(n):
    train_type = RNG.choice(TYPES, size=n, p=TYPE_P)
    journey_hours = np.round(RNG.uniform(1.5, 38, size=n), 1)
    dep_hour = RNG.integers(0, 24, size=n)
    # fare per hour: premium types cost more per hour; add spread
    base_fph = np.array([
        {"Raj": 230, "Shtb": 240, "Drnt": 170, "GR": 160}.get(t, 95) for t in train_type
    ])
    fare_per_hour = np.clip(base_fph + RNG.normal(0, 35, size=n), 25, 500)

    quality = np.array([TYPE_QUALITY[t] for t in train_type])
    conv = _dep_convenience(dep_hour)

    score = (
        62.0
        - 1.15 * journey_hours          # shorter journeys are strongly preferred
        + quality                       # comfort / punctuality of the type
        + conv                          # convenient departure time
        - 0.035 * fare_per_hour         # value for money
        + RNG.normal(0, 4.0, size=n)    # taste noise
    )
    score = np.clip(score, 0, 100)

    return pd.DataFrame({
        "train_type": train_type,
        "journey_hours": journey_hours,
        "dep_hour": dep_hour,
        "fare_per_hour": np.round(fare_per_hour, 1),
        "match_score": np.round(score, 1),
    })


def main():
    df = make_dataset(N)
    X = df.drop(columns=["match_score"])
    y = df["match_score"]

    cat = ["train_type"]
    num = ["journey_hours", "dep_hour", "fare_per_hour"]
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
        ("num", "passthrough", num),
    ])
    model = Pipeline([
        ("pre", pre),
        ("reg", GradientBoostingRegressor(random_state=11)),
    ])

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=11)
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)

    print(f"samples : {N:,}")
    print(f"R2      : {r2_score(yte, pred):.3f}")
    print(f"MAE     : {mean_absolute_error(yte, pred):.2f} points")

    joblib.dump(model, "model_rank.joblib")
    print("saved -> model_rank.joblib")


if __name__ == "__main__":
    main()