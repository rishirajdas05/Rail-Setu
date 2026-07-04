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


def _stop_based_results(from_codes, to_codes):
    """Rich search using the Stop (schedule) table. Empty if no stops loaded."""
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
    if not candidate_ids:
        return []

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
    return results


def _endpoint_based_results(from_codes, to_codes):
    """Fallback when no schedule/stop data is loaded: match a train's own
    source and destination stations. Covers endpoint-to-endpoint routes."""
    trains = Train.objects.filter(
        source_id__in=from_codes, destination_id__in=to_codes
    ).only("number", "name", "train_type", "runs_on", "source_id", "destination_id")

    codes = set(from_codes) | set(to_codes)
    for t in trains:
        codes.add(t.source_id)
        codes.add(t.destination_id)
    names = dict(Station.objects.filter(code__in=codes).values_list("code", "name"))

    results = []
    for t in trains:
        results.append({
            "number": t.number,
            "name": t.name,
            "type": t.train_type,
            "origin": {
                "code": t.source_id,
                "name": names.get(t.source_id, ""),
                "time": None,
                "day": 1,
            },
            "destination": {
                "code": t.destination_id,
                "name": names.get(t.destination_id, ""),
                "time": None,
                "day": 1,
            },
            "duration": None,
            "runs_on": t.runs_on,
        })
    return results


def search_trains(from_codes, to_codes, journey_date=None):
    """
    Trains from any 'from' station to any 'to' station.

    Prefers the detailed schedule (Stop) data when it is loaded, which supports
    through-station matches and real timings. When no stop data is present,
    falls back to matching each train's own source/destination stations so
    endpoint-to-endpoint routes still work.
    """
    from_codes = [c.upper() for c in from_codes]
    to_codes = [c.upper() for c in to_codes]

    results = _stop_based_results(from_codes, to_codes)
    if not results:
        results = _endpoint_based_results(from_codes, to_codes)

    results.sort(key=lambda r: (
        r["origin"]["time"] is None,
        r["origin"]["time"] or datetime.min.time(),
        r["number"],
    ))
    return results