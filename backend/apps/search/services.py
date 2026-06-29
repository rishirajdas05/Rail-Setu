"""Train search: find trains running from one station/city to another."""

from datetime import datetime, timedelta

from apps.stations.models import Station
from apps.trains.models import Stop, Train


def _format_duration(dep, arr, day_diff):
    if not dep or not arr:
        return None
    base = datetime(2000, 1, 1)
    dep_dt = base.replace(hour=dep.hour, minute=dep.minute, second=dep.second)
    arr_dt = (base + timedelta(days=max(day_diff, 0))).replace(
        hour=arr.hour, minute=arr.minute, second=arr.second
    )
    minutes = int((arr_dt - dep_dt).total_seconds() // 60)
    if minutes < 0:
        minutes += 24 * 60
    return f"{minutes // 60}h {minutes % 60:02d}m"


def search_trains(from_codes, to_codes, journey_date=None):
    """
    Trains that depart from any 'from' station and later reach any 'to' station.

    from_codes / to_codes are lists (a single station is a one-item list; a city
    is its list of terminals). For each train we pick the earliest boarding
    terminal and the latest reachable destination terminal, so the result shows
    the actual stations that train uses.
    """
    from_codes = [c.upper() for c in from_codes]
    to_codes = [c.upper() for c in to_codes]

    from_map = {}
    for s in Stop.objects.filter(station_id__in=from_codes).values(
        "train_id", "station_id", "sequence", "departure", "day_offset"
    ):
        from_map.setdefault(s["train_id"], []).append(s)

    to_map = {}
    for s in Stop.objects.filter(station_id__in=to_codes).values(
        "train_id", "station_id", "sequence", "arrival", "day_offset"
    ):
        to_map.setdefault(s["train_id"], []).append(s)

    candidate_ids = [t for t in from_map if t in to_map]
    names = dict(
        Station.objects.filter(
            code__in=set(from_codes) | set(to_codes)
        ).values_list("code", "name")
    )
    trains = Train.objects.filter(number__in=candidate_ids).only(
        "number", "name", "train_type", "runs_on"
    )

    results = []
    for t in trains:
        fs = min(from_map[t.number], key=lambda x: x["sequence"])
        reachable = [x for x in to_map[t.number] if x["sequence"] > fs["sequence"]]
        if not reachable:
            continue
        ts = max(reachable, key=lambda x: x["sequence"])


        day_diff = ts["day_offset"] - fs["day_offset"]
        results.append({
            "number": t.number,
            "name": t.name,
            "type": t.train_type,
            "origin": {
                "code": fs["station_id"],
                "name": names.get(fs["station_id"], ""),
                "time": fs["departure"],
                "day": fs["day_offset"] + 1,
            },
            "destination": {
                "code": ts["station_id"],
                "name": names.get(ts["station_id"], ""),
                "time": ts["arrival"],
                "day": ts["day_offset"] + 1,
            },
            "duration": _format_duration(fs["departure"], ts["arrival"], day_diff),
            "runs_on": t.runs_on,
        })

    results.sort(key=lambda r: (r["origin"]["time"] is None, r["origin"]["time"] or datetime.min.time()))
    return results