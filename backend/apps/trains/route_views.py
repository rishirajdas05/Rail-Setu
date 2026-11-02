from datetime import datetime, timedelta
from math import radians, sin, cos, asin, sqrt
from zoneinfo import ZoneInfo

from django.http import JsonResponse

from apps.trains.models import Train, Stop

IST = ZoneInfo("Asia/Kolkata")


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


def _mins(t, day_offset):
    if t is None:
        return None
    return day_offset * 24 * 60 + t.hour * 60 + t.minute


def _started_days_ago(started):
    table = {"today": 0, "yesterday": 1, "2": 2, "3": 3}
    return table.get(str(started).lower(), 0)


def train_route(request, number):
    try:
        train = Train.objects.select_related("source", "destination").get(number=number)
    except Train.DoesNotExist:
        return JsonResponse({"detail": "Train not found."}, status=404)

    stops_qs = Stop.objects.filter(train=train).select_related("station").order_by("sequence")

    stops = []
    prev = None
    cum_km = 0.0
    for s in stops_qs:
        st = s.station
        if st is None or st.latitude is None or st.longitude is None:
            continue
        lat, lon = float(st.latitude), float(st.longitude)
        if prev is not None:
            cum_km += _haversine_km(prev[0], prev[1], lat, lon)
        prev = (lat, lon)
        stops.append({
            "code": st.code,
            "name": st.name,
            "lat": lat,
            "lon": lon,
            "sequence": s.sequence,
            "arrival": s.arrival.strftime("%H:%M") if s.arrival else None,
            "departure": s.departure.strftime("%H:%M") if s.departure else None,
            "day_offset": s.day_offset,
            "_dep_min": _mins(s.departure, s.day_offset),
            "_arr_min": _mins(s.arrival, s.day_offset),
            "_km": round(cum_km, 1),
        })

    if len(stops) < 2:
        return JsonResponse({"detail": "Route has too few mapped stations."}, status=422)

    total_km = stops[-1]["_km"]

    origin_min = stops[0]["_dep_min"] if stops[0]["_dep_min"] is not None else 0
    dest_min = stops[-1]["_arr_min"]
    if dest_min is None:
        dest_min = stops[-1]["_dep_min"]
    journey_min = max((dest_min or origin_min) - origin_min, 0)
    avg_speed = round(total_km / (journey_min / 60), 1) if journey_min else None

    days_ago = _started_days_ago(request.GET.get("started", "today"))
    now = datetime.now(IST)
    origin_departure = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)
    elapsed = (now - origin_departure).total_seconds() / 60.0

    current = None
    status_text = None
    if elapsed <= origin_min:
        status_text = "Not started yet"
        current = {"lat": stops[0]["lat"], "lon": stops[0]["lon"], "after": None, "next": stops[0]["code"], "covered_km": 0.0}
    elif elapsed >= (dest_min if dest_min else 0):
        status_text = "Completed"
        current = {"lat": stops[-1]["lat"], "lon": stops[-1]["lon"], "after": stops[-1]["code"], "next": None, "covered_km": total_km}
    else:
        for i in range(len(stops) - 1):
            a, b = stops[i], stops[i + 1]
            a_leave = a["_dep_min"] if a["_dep_min"] is not None else a["_arr_min"]
            b_reach = b["_arr_min"] if b["_arr_min"] is not None else b["_dep_min"]
            if a_leave is None or b_reach is None or b_reach <= a_leave:
                continue
            if a_leave <= elapsed <= b_reach:
                frac = (elapsed - a_leave) / (b_reach - a_leave)
                lat = a["lat"] + (b["lat"] - a["lat"]) * frac
                lon = a["lon"] + (b["lon"] - a["lon"]) * frac
                covered = a["_km"] + (b["_km"] - a["_km"]) * frac
                current = {"lat": round(lat, 5), "lon": round(lon, 5), "after": a["code"], "next": b["code"], "covered_km": round(covered, 1)}
                status_text = "Crossed %s at %s, next stop %s" % (a["name"], a["departure"] or a["arrival"], b["name"])
                break
        if current is None:
            status_text = "At a station"
            current = {"lat": stops[0]["lat"], "lon": stops[0]["lon"], "after": None, "next": None, "covered_km": 0.0}

    for s in stops:
        s.pop("_dep_min", None)
        s.pop("_arr_min", None)
        s["km"] = s.pop("_km")

    return JsonResponse({
        "number": train.number,
        "name": train.name,
        "source": train.source_id,
        "destination": train.destination_id,
        "stats": {
            "total_km": round(total_km, 1),
            "journey_minutes": journey_min,
            "avg_speed_kmph": avg_speed,
            "halts": len(stops),
        },
        "polyline": [[s["lat"], s["lon"]] for s in stops],
        "stops": stops,
        "current": current,
        "status_text": status_text,
        "indicative": True,
    })


