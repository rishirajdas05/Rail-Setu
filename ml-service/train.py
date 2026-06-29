"""
Train the RailSetu waitlist-confirmation predictor.

IMPORTANT: This model is trained on SYNTHETIC data. Indian Railways does not
publish historical PNR/waitlist outcomes, so we generate a dataset whose
patterns follow real domain rules (waitlist position, days to journey, quota,
class capacity, weekday demand) and train a genuine scikit-learn model on it.
The pipeline (feature engineering -> training -> serialization -> serving) is
real; only the training data is simulated. Do not present its probabilities as
based on real railway records.

Run:  python train.py
Out:  model.joblib  (a full sklearn Pipeline incl. preprocessing)
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, accuracy_score, brier_score_loss
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
import joblib

RNG = np.random.default_rng(42)
N = 40_000

CLASSES = ["1A", "2A", "3A", "SL", "CC", "2S"]
QUOTAS = ["GN", "TQ", "LD", "SS"]

# Relative seat capacity per class (bigger pool -> waitlists clear more easily).
CLASS_CAPACITY = {"1A": 0.30, "2A": 0.55, "3A": 1.0, "SL": 1.4, "CC": 0.8, "2S": 1.2}
# Quota effect on clearance (Tatkal barely clears; senior/ladies have priority pools).
QUOTA_FACTOR = {"GN": 1.0, "TQ": 0.45, "LD": 1.15, "SS": 1.2}


def make_dataset(n):
    travel_class = RNG.choice(CLASSES, size=n, p=[0.05, 0.12, 0.25, 0.38, 0.10, 0.10])
    quota = RNG.choice(QUOTAS, size=n, p=[0.78, 0.12, 0.05, 0.05])
    waitlist_position = RNG.integers(1, 120, size=n)
    days_to_journey = RNG.integers(0, 120, size=n)
    journey_dow = RNG.integers(0, 7, size=n)  # 0=Mon ... 6=Sun

    cap = np.array([CLASS_CAPACITY[c] for c in travel_class])
    qf = np.array([QUOTA_FACTOR[q] for q in quota])
    weekend = np.isin(journey_dow, [4, 5, 6]).astype(float)  # Fri/Sat/Sun busier

    # latent log-odds of confirmation
    z = (
        2.1
        - 0.045 * waitlist_position / cap        # deeper waitlist, smaller class -> worse
        + 0.022 * days_to_journey                # more lead time -> more cancellations clear WL
        + 1.4 * (qf - 1.0)                        # quota pool effect
        - 0.55 * weekend                          # weekend demand
        + RNG.normal(0, 0.6, size=n)             # irreducible noise
    )
    prob = 1.0 / (1.0 + np.exp(-z))
    confirmed = (RNG.random(n) < prob).astype(int)

    return pd.DataFrame({
        "travel_class": travel_class,
        "quota": quota,
        "waitlist_position": waitlist_position,
        "days_to_journey": days_to_journey,
        "journey_dow": journey_dow,
        "confirmed": confirmed,
    })


def main():
    df = make_dataset(N)
    X = df.drop(columns=["confirmed"])
    y = df["confirmed"]

    cat = ["travel_class", "quota"]
    num = ["waitlist_position", "days_to_journey", "journey_dow"]

    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
        ("num", "passthrough", num),
    ])
    model = Pipeline([
        ("pre", pre),
        ("clf", GradientBoostingClassifier(random_state=42)),
    ])

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    model.fit(Xtr, ytr)

    p = model.predict_proba(Xte)[:, 1]
    print(f"samples        : {N:,}")
    print(f"base confirm % : {y.mean()*100:.1f}")
    print(f"ROC AUC        : {roc_auc_score(yte, p):.3f}")
    print(f"accuracy       : {accuracy_score(yte, (p >= 0.5).astype(int)):.3f}")
    print(f"brier (cal.)   : {brier_score_loss(yte, p):.3f}")

    joblib.dump(model, "model.joblib")
    print("saved -> model.joblib")


if __name__ == "__main__":
    main()