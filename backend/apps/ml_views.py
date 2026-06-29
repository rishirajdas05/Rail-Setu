"""Proxy + feature assembly from Django to the FastAPI ML service.

Confirmation: thin pass-through (the client already has the inputs).
Delay: Django assembles the model's features from the train's schedule, so the
client only needs to send a train number and date.
"""

from datetime import date as date_cls

import requests
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.trains.models import Train


def _ml_base():
    return getattr(settings, "ML_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")


def _post(path, payload):
    """POST to the ML service, returning (data, status)."""
    try:
        r = requests.post(f"{_ml_base()}{path}", json=payload, timeout=5)
        return r.json(), r.status_code
    except requests.exceptions.ConnectionError:
        return {"detail": "Prediction service is offline. Start the ML service on port 8001."}, 503
    except requests.exceptions.RequestException as exc:
        return {"detail": f"Prediction service error: {exc}"}, 502


class ConfirmationPredictView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from apps.analytics.models import record
        record("predict_confirmation")
        data, status = _post("/predict/confirmation", request.data)
        return Response(data, status=status)


class RankPredictView(APIView):
    """POST /api/predict/rank/  — thin pass-through; client sends the train list."""

    permission_classes = [AllowAny]

    def post(self, request):
        from apps.analytics.models import record
        record("predict_rank")
        data, status = _post("/predict/rank", request.data)
        return Response(data, status=status)


class DelayPredictView(APIView):
    """GET /api/predict/delay/?train=12138&date=2026-07-01"""

    permission_classes = [AllowAny]

    def get(self, request):
        from apps.analytics.models import record
        record("predict_delay")
        number = request.query_params.get("train")
        if not number:
            return Response({"detail": "train query param is required."}, status=400)

        try:
            train = Train.objects.prefetch_related("stops").get(number=number)
        except Train.DoesNotExist:
            return Response({"detail": f"Train {number} not found."}, status=404)

        stops = list(train.stops.all().order_by("sequence"))
        timed = [s for s in stops if (s.arrival or s.departure)]
        if len(timed) < 2:
            return Response({"detail": "Not enough schedule to estimate delay."}, status=422)

        first, last = timed[0], timed[-1]
        dep = first.departure or first.arrival
        arr = last.arrival or last.departure

        start = first.day_offset * 1440 + dep.hour * 60 + dep.minute
        end = last.day_offset * 1440 + arr.hour * 60 + arr.minute
        journey_min = end - start
        if journey_min <= 0:
            journey_min += 1440

        d_str = request.query_params.get("date")
        try:
            d = date_cls.fromisoformat(d_str) if d_str else date_cls.today()
        except ValueError:
            d = date_cls.today()

        features = {
            "train_type": train.train_type or "Exp",
            "journey_hours": round(journey_min / 60.0, 1),
            "num_stops": min(len(timed), 60),
            "dep_hour": dep.hour,
            "journey_dow": d.weekday(),
            "month": d.month,
        }
        data, status = _post("/predict/delay", features)
        if status == 200:
            data["train_number"] = train.number
            data["train_name"] = train.name
        return Response(data, status=status)