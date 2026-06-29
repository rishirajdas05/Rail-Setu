# RailSetu ML Service

A standalone FastAPI microservice that predicts the chance a waitlisted ticket
gets confirmed. It is separate from the Django app and talks to it over HTTP.

## Important: synthetic data
Indian Railways does not publish historical PNR/waitlist outcomes, so the model
is trained on a **synthetically generated** dataset whose patterns follow real
domain rules (waitlist position, days to journey, quota, class capacity, weekday
demand). The ML pipeline is real; the training data is simulated. The API labels
every response with a disclaimer.

## Setup
```
cd ml-service
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
python train.py            # generates model.joblib (prints AUC ~0.86)
uvicorn app:app --reload --port 8001
```

Interactive docs: http://127.0.0.1:8001/docs

## Endpoints
- `GET /health`
- `POST /predict/confirmation`
  ```json
  { "travel_class": "SL", "quota": "GN", "waitlist_position": 22, "journey_date": "2026-07-01" }
  ```
  returns
  ```json
  { "confirmation_probability": 0.62, "percent": 62, "band": "Moderate", "prediction": "likely to confirm" }
  ```

`travel_class` in 1A,2A,3A,SL,CC,2S · `quota` in GN,TQ,LD,SS.