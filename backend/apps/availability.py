"""Seat availability, ixigo-style, for a train on a date.

Honest note: live IRCTC seat counts require the authorized booking feed, which
this project does not have. So availability here is SYNTHETIC but deterministic:
the same train + date + class always yields the same status (seeded by a hash),
so it behaves like a stable snapshot rather than random noise. Waitlist
confirmation chance is supplied by the real confirmation model. Every response
is labelled accordingly.
"""

import hashlib
from datetime import date as date_cls
from decimal import Decimal

import requests
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.trains.models import Train

CLASS_NAMES = {
    "1A": "AC First", "2A": "AC 2 Tier", "3A": "AC 3 Tier",
    "SL": "Sleeper", "CC": "Chair Car", "2S": "Second Sitting",
    "EC": "Executive Chair",
}

# Real Indian Railways fares are distance-based. The seed dataset has no
# distances, so we estimate segment distance from the segment's travel time and
# a per-type average speed, then price it per km. Still an estimate, but it now
# tracks the searched leg and the class realistically.
FARE_PER_KM = {
    "1A": 4.5, "2A": 2.6, "3A": 1.8, "SL": 0.6, "CC": 1.6, "2S": 0.45, "EC": 3.2,
}
RES_CHARGE = {
    "1A": 60, "2A": 50, "3A": 40, "SL": 20, "CC": 40, "2S": 15, "EC": 60,
}
TYPE_SPEED = {  # approx avg km/h, used to turn travel time into distance
    "Shtb": 85, "JShtb": 85, "Raj": 85, "Drnt": 80, "GR": 80,
    "SF": 65, "SKr": 62, "Hyd": 60, "Exp": 55, "Mail": 55,
    "Pass": 38, "MEMU": 40, "Hybrid": 50,
}
PREMIUM_MULT = {  # catering / premium surcharge
    "Shtb": 1.5, "JShtb": 1.5, "Raj": 1.5, "Drnt": 1.45, "GR": 1.45,
    "SF": 1.15, "SKr": 1.15, "Hyd": 1.1,
}

_PREMIUM = ["3A", "2A", "1A"]
_CHAIR = ["CC", "EC"]
_STD = ["SL", "3A", "2A"]
CLASS_BY_TYPE = {
    "Raj": _PREMIUM, "GR": _PREMIUM, "Drnt": ["SL"] + _PREMIUM,
    "Shtb": _CHAIR, "JShtb": _CHAIR,
    "SF": ["SL", "3A", "2A"], "Exp": ["SL", "3A", "2A"], "Mail": ["SL", "3A", "2A", "1A"],
    "Hyd": _STD, "SKr": _STD, "Pass": ["2S", "SL"], "MEMU": ["2S"],
}

# per class: chance of being available, chance of RAC, and a waitlist ceiling
_AVL_P = {"1A": 0.55, "2A": 0.45, "3A": 0.32, "SL": 0.18, "CC": 0.52, "2S": 0.64}
_RAC_P = {"1A": 0.06, "2A": 0.10, "3A": 0.13, "SL": 0.16, "CC": 0.06, "2S": 0.05}
_WL_MAX = {"1A": 8, "2A": 30, "3A": 60, "SL": 120, "CC": 40, "2S": 70}


def _seed(train, date, cls, quota="GN"):
    h = hashlib.md5(f"{train}|{date}|{cls}|{quota}".encode()).hexdigest()
    return int(h[:8], 16)


def _est_distance(hours, train_type):
    speed = TYPE_SPEED.get(train_type, 55)
    return max(hours * speed, 30.0)


# Approx Tatkal surcharge per class (fixed band, like IRCTC). 1A has no Tatkal.
TATKAL_CHARGE = {"2S": 15, "SL": 150, "CC": 175, "3A": 350, "2A": 450, "EC": 450, "1A": 0}


def _fare(cls, distance_km, train_type, quota="GN"):
    per_km = FARE_PER_KM.get(cls, 1.0)
    mult = PREMIUM_MULT.get(train_type, 1.0)
    res = RES_CHARGE.get(cls, 30)
    amount = per_km * distance_km * mult + res
    if quota == "TQ":
        amount += TATKAL_CHARGE.get(cls, 200)
    return int(round(amount / 5.0) * 5)  # round to nearest 5


def _segment_hours(train, from_code, to_code):
    """Travel time (hours) for the searched leg, or None if it can't be resolved."""
    if not from_code or not to_code:
        return None
    stops = {s.station_id: s for s in train.stops.all()}
    a = stops.get(str(from_code).upper())
    b = stops.get(str(to_code).upper())
    if not a or not b:
        return None
    dep = a.departure or a.arrival
    arr = b.arrival or b.departure
    if not dep or not arr:
        return None
    mins = (b.day_offset * 1440 + arr.hour * 60 + arr.minute) - \
           (a.day_offset * 1440 + dep.hour * 60 + dep.minute)
    if mins <= 0:
        mins += 1440
    return round(mins / 60.0, 2)


def seat_pool(seed, cls, quota="GN"):
    """The numeric seat pool behind the displayed status. Booking uses this too,
    so what you see on the train page is what you get when you book."""
    r = (seed % 1000) / 1000.0
    avl, rac = _AVL_P.get(cls, 0.3), _RAC_P.get(cls, 0.12)
    if quota == "TQ":
        avl *= 0.45  # Tatkal quota is a small pool that fills fast
        rac *= 0.6
    if r < avl:
        n = (seed >> 8) % 60 + 2
        return {"kind": "available", "available": n, "rac": 0, "waitlist": 0}
    if r < avl + rac:
        n = (seed >> 9) % 18 + 1
        return {"kind": "rac", "available": 0, "rac": n, "waitlist": 0}
    wl = (seed >> 10) % _WL_MAX.get(cls, 60) + 1
    if wl > 0.85 * _WL_MAX.get(cls, 60):
        return {"kind": "regret", "available": 0, "rac": 0, "waitlist": wl}
    return {"kind": "waitlist", "available": 0, "rac": 0, "waitlist": wl}


def _status(cls, seed, quota="GN"):
    """Return (status_type, label, waitlist_number)."""
    p = seat_pool(seed, cls, quota)
    if p["kind"] == "available":
        return "available", f"AVL {p['available']}", 0
    if p["kind"] == "rac":
        return "rac", f"RAC {p['rac']}", 0
    if p["kind"] == "regret":
        return "regret", "Regret", p["waitlist"]
    return "waitlist", f"WL {p['waitlist']}", p["waitlist"]


def _journey_hours(train):
    stops = [s for s in train.stops.all().order_by("sequence") if (s.arrival or s.departure)]
    if len(stops) >= 2:
        a, b = stops[0], stops[-1]
        dep = a.departure or a.arrival
        arr = b.arrival or b.departure
        mins = (b.day_offset * 1440 + arr.hour * 60 + arr.minute) - \
               (a.day_offset * 1440 + dep.hour * 60 + dep.minute)
        if mins <= 0:
            mins += 1440
        return round(mins / 60.0, 1)
    return 12.0


class AvailabilityView(APIView):
    """GET /api/availability/?train=12138&date=2026-07-01"""

    permission_classes = [AllowAny]

    def get(self, request):
        number = request.query_params.get("train")
        if not number:
            return Response({"detail": "train query param is required."}, status=400)
        try:
            train = Train.objects.prefetch_related("stops").get(number=number)
        except Train.DoesNotExist:
            return Response({"detail": f"Train {number} not found."}, status=404)

        seg = _segment_hours(train, request.query_params.get("from"),
                             request.query_params.get("to"))
        hours = seg or _journey_hours(train)
        distance = _est_distance(hours, train.train_type)

        d_str = request.query_params.get("date")
        try:
            d = date_cls.fromisoformat(d_str) if d_str else date_cls.today()
        except ValueError:
            d = date_cls.today()

        classes = CLASS_BY_TYPE.get(train.train_type, _STD)
        base = getattr(settings, "ML_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")

        quota = request.query_params.get("quota", "GN").upper()
        if quota not in ("GN", "TQ"):
            quota = "GN"
        # 1A is not offered under Tatkal
        if quota == "TQ":
            classes = [c for c in classes if c != "1A"] or classes

        out = []
        for cls in classes:
            seed = _seed(train.number, d.isoformat(), cls, quota)
            kind, label, wl = _status(cls, seed, quota)
            item = {
                "travel_class": cls,
                "class_name": CLASS_NAMES.get(cls, cls),
                "fare": _fare(cls, distance, train.train_type, quota),
                "status_type": kind,
                "status": label,
                "chance": None,
            }
            if kind == "waitlist" and wl:
                try:
                    r = requests.post(
                        f"{base}/predict/confirmation",
                        json={"travel_class": cls, "quota": quota,
                              "waitlist_position": wl, "journey_date": d.isoformat()},
                        timeout=4,
                    )
                    if r.ok:
                        item["chance"] = r.json().get("percent")
                except requests.exceptions.RequestException:
                    pass
            out.append(item)

        return Response({
            "train_number": train.number,
            "train_name": train.name,
            "date": d.isoformat(),
            "quota": quota,
            "classes": out,
            "disclaimer": "Availability is simulated for demonstration; confirmation chance uses the ML model.",
        })


class WeekAvailabilityView(APIView):
    """GET /api/availability/week/?train=12138&from=2026-06-19

    Deterministic 7-day availability grid (no per-cell ML call, so it's fast).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        from datetime import timedelta

        number = request.query_params.get("train")
        if not number:
            return Response({"detail": "train query param is required."}, status=400)
        try:
            train = Train.objects.prefetch_related("stops").get(number=number)
        except Train.DoesNotExist:
            return Response({"detail": f"Train {number} not found."}, status=404)

        d_str = request.query_params.get("date") or request.query_params.get("from_date")
        try:
            start = date_cls.fromisoformat(d_str) if d_str else date_cls.today()
        except ValueError:
            start = date_cls.today()

        seg = _segment_hours(train, request.query_params.get("from"),
                             request.query_params.get("to"))
        hours = seg or _journey_hours(train)
        distance = _est_distance(hours, train.train_type)
        classes = CLASS_BY_TYPE.get(train.train_type, _STD)

        days = []
        for i in range(7):
            d = start + timedelta(days=i)
            cells = {}
            for cls in classes:
                kind, label, wl = _status(cls, _seed(train.number, d.isoformat(), cls))
                cells[cls] = {"status_type": kind, "status": label}
            days.append({
                "date": d.isoformat(),
                "weekday": d.strftime("%a"),
                "day": d.strftime("%d %b"),
                "cells": cells,
            })

        return Response({
            "train_number": train.number,
            "train_name": train.name,
            "classes": classes,
            "class_names": {c: CLASS_NAMES.get(c, c) for c in classes},
            "fares": {c: _fare(c, distance, train.train_type) for c in classes},
            "days": days,
            "disclaimer": "Availability is simulated for demonstration only.",
        })