import time
from datetime import datetime, timedelta
from math import radians, degrees, sin, cos, atan2
from zoneinfo import ZoneInfo

from django.http import JsonResponse

from apps.trains.models import Stop

IST = ZoneInfo("Asia/Kolkata")

_CACHE = {"key": None, "at": 0.0, "data": None}
_CACHE_TTL = 60


def _mins(t, day_offset):
    if t is None:
        return None
    return day_offset * 24 * 60 + t.hour * 60 + t.minute


def _started_days_ago(started):
    return {"today": 0, "yesterday": 1, "2": 2, "3": 3}.get(str(started).lower(), 0)


def _bearing(lat1, lon1, lat2, lon2):
    p1, p2 = radians(lat1), radians(lat2)
    dl = radians(lon2 - lon1)
    y = sin(dl) * cos(p2)
    x = cos(p1) * sin(p2) - sin(p1) * cos(p2) * cos(dl)
    return (degrees(atan2(y, x)) + 360) % 360


def _position_for(stops, elapsed):
    first, last = stops[0], stops[-1]
    origin_min = first[2] if first[2] is not None else (first[3] or 0)
    dest_min = last[3] if last[3] is not None else last[2]
    if dest_min is None or elapsed <= origin_min or elapsed >= dest_min:
        return None
    for i in range(len(stops) - 1):
        a, b = stops[i], stops[i + 1]
        a_leave = a[2] if a[2] is not None else a[3]
        b_reach = b[3] if b[3] is not None else b[2]
        if a_leave is None or b_reach is None or b_reach <= a_leave:
            continue
        if a_leave <= elapsed <= b_reach:
            frac = (elapsed - a_leave) / (b_reach - a_leave)
            lat = a[0] + (b[0] - a[0]) * frac
            lon = a[1] + (b[1] - a[1]) * frac
            brg = _bearing(a[0], a[1], b[0], b[1])
            return (lat, lon, brg)
    return None


def radar(request):
    started = request.GET.get("started", "today")
    now = datetime.now(IST)
    days_ago = _started_days_ago(started)
    origin_departure = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)
    elapsed = (now - origin_departure).total_seconds() / 60.0

    cache_key = (started, int(elapsed // 2))
    if _CACHE["key"] == cache_key and (time.time() - _CACHE["at"]) < _CACHE_TTL:
        return JsonResponse(_CACHE["data"])

    rows = (
        Stop.objects.select_related("station", "train")
        .order_by("train_id", "sequence")
        .values_list("train_id", "train__name", "station__latitude", "station__longitude", "departure", "arrival", "day_offset")
    )

    by_train = {}
    for train_id, name, lat, lon, dep, arr, day in rows:
        if lat is None or lon is None:
            continue
        by_train.setdefault(train_id, {"name": name, "stops": []})
        by_train[train_id]["stops"].append((float(lat), float(lon), _mins(dep, day), _mins(arr, day)))

    trains = []
    for train_id, info in by_train.items():
        stops = info["stops"]
        if len(stops) < 2:
            continue
        pos = _position_for(stops, elapsed)
        if pos is None:
            continue
        trains.append({"number": train_id, "name": info["name"], "lat": round(pos[0], 5), "lon": round(pos[1], 5), "bearing": round(pos[2])})

    data = {"count": len(trains), "trains": trains, "indicative": True}
    _CACHE.update(key=cache_key, at=time.time(), data=data)
    return JsonResponse(data)
