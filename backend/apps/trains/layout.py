"""Indicative platform numbers and coach ordering.

The 2016 seed dataset has no platform or coach-position data, so these are
deterministic, plausible stand-ins (stable per train/station), clearly labelled
as indicative in the UI. Same train + station always yields the same platform.
"""

import hashlib

from apps.availability import CLASS_BY_TYPE, CLASS_NAMES, _STD


def _h(*parts):
    return int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def platform_for(train_key, station_code):
    """A stable platform number for a train at a station."""
    max_plat = 4 + (_h("plat", station_code) % 12)  # station has 4..15 platforms
    return (_h(train_key, station_code) % max_plat) + 1


COACH_PREFIX = {"1A": "H", "2A": "A", "3A": "B", "SL": "S", "CC": "C", "2S": "D", "EC": "E"}
_BASE_COUNT = {"SL": 5, "3A": 2, "2A": 1, "1A": 1, "CC": 5, "EC": 1, "2S": 3}


def coach_layout(train):
    """An ordered, indicative coach sequence (front to back) for a train."""
    classes = CLASS_BY_TYPE.get(train.train_type, _STD)

    def count(cls):
        return _BASE_COUNT.get(cls, 2) + (_h(train.number, cls) % 2)

    coaches = [{"code": "SLR", "cls": None, "name": "Guard / luggage"}]

    if "2S" in classes:
        for i in range(1, count("2S") + 1):
            coaches.append({"code": f"D{i}", "cls": "2S", "name": CLASS_NAMES.get("2S", "Second sitting")})
    else:
        coaches += [
            {"code": "GS1", "cls": None, "name": "Unreserved"},
            {"code": "GS2", "cls": None, "name": "Unreserved"},
        ]

    if "SL" in classes:
        for i in range(1, count("SL") + 1):
            coaches.append({"code": f"S{i}", "cls": "SL", "name": CLASS_NAMES.get("SL", "Sleeper")})

    has_ac = any(c in classes for c in ("3A", "2A", "1A"))
    if has_ac and "SL" in classes:
        coaches.append({"code": "PC", "cls": None, "name": "Pantry car"})

    for cls in ("3A", "CC", "EC", "2A", "1A"):
        if cls in classes:
            for i in range(1, count(cls) + 1):
                coaches.append({
                    "code": f"{COACH_PREFIX[cls]}{i}",
                    "cls": cls,
                    "name": CLASS_NAMES.get(cls, cls),
                })

    coaches.append({"code": "SLR", "cls": None, "name": "Guard / luggage"})
    return coaches