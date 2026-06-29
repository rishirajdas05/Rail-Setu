"""
Client + normalizer for a third-party Indian Railways live-data provider.

Configured through settings/env, so the app works with no key (returning a
clear "not configured" result) and goes live once a key is set.

Wired for the RapidAPI "Indian Railway IRCTC" provider
(host indian-railway-irctc.p.rapidapi.com). Its live-status endpoint takes a
train_number and a departure_date (YYYYMMDD, the day the train left its origin),
and authenticates with the RapidAPI key/host headers plus an extra
"x-rapid-api" header. The UI passes a start_day (0 = today, 1 = yesterday, ...)
which we convert to that departure_date.
"""

import hashlib
import re
from datetime import date, datetime, timedelta

import requests
from django.conf import settings
from django.core.cache import cache


def _get(name, default=""):
    return getattr(settings, name, default)


def _departure_date(start_day):
    try:
        n = int(start_day)
    except (TypeError, ValueError):
        n = 0
    return (date.today() - timedelta(days=max(0, n))).strftime("%Y%m%d")


# ---------------------------------------------------------------- API calls

def running_status(train_number, start_day="1"):
    if not _get("LIVE_API_KEY"):
        return _not_configured("running status")
    url = _get("LIVE_RUNNING_STATUS_URL").format(
        train=train_number, departure_date=_departure_date(start_day))
    return _call(url, cache_ttl=_get("LIVE_CACHE_TTL", 120))


def pnr_status(pnr):
    if not _get("LIVE_API_KEY"):
        return _not_configured("PNR")
    url = _get("LIVE_PNR_STATUS_URL").format(pnr=pnr)
    return _call(url, cache_ttl=_get("LIVE_PNR_CACHE_TTL", 300))


def _not_configured(what):
    return {
        "configured": False,
        "detail": f"Live {what} is not configured. Set LIVE_API_KEY in the environment.",
    }


def _call(url, cache_ttl=0):
    ckey = None
    if cache_ttl:
        ckey = "live:" + hashlib.md5(url.encode()).hexdigest()
        hit = cache.get(ckey)
        if hit is not None:
            return {**hit, "cached": True}

    headers = {}
    host = _get("LIVE_API_HOST")
    if host:  # RapidAPI providers authenticate with headers.
        headers = {"X-RapidAPI-Key": _get("LIVE_API_KEY"), "X-RapidAPI-Host": host}
        extra = _get("LIVE_API_EXTRA_HEADER")  # e.g. "x-rapid-api: rapid-api-database"
        if extra and ":" in extra:
            name, value = extra.split(":", 1)
            headers[name.strip()] = value.strip()
    try:
        resp = requests.get(url, headers=headers, timeout=_get("LIVE_API_TIMEOUT", 8))
    except requests.exceptions.Timeout:
        return {"configured": True, "error": "timeout",
                "detail": "The live provider timed out. Try again."}
    except requests.exceptions.RequestException as exc:
        print(f"[live] request failed: {type(exc).__name__}: {exc}")
        return {"configured": True, "error": "request_failed",
                "detail": f"Could not reach the live provider ({type(exc).__name__})."}

    if resp.status_code == 429:
        return {"configured": True, "error": "rate_limited",
                "detail": "Live status is rate-limited on the free plan. Wait a minute and try again."}
    if resp.status_code in (401, 403):
        return {"configured": True, "error": "auth",
                "detail": "The live provider rejected the request. Check your API key, host, and subscription."}
    if resp.status_code >= 400:
        snippet = (resp.text or "")[:200].replace("\n", " ")
        print(f"[live] HTTP {resp.status_code} from provider: {snippet}")
        return {"configured": True, "error": f"http_{resp.status_code}",
                "detail": f"Provider returned HTTP {resp.status_code}. {snippet}"}
    try:
        result = {"configured": True, "source": "live", "data": resp.json()}
    except ValueError:
        return {"configured": True, "error": "non_json",
                "detail": "Provider returned a non-JSON response."}

    # cache only successful responses, so errors/rate-limits never get stuck
    if ckey:
        cache.set(ckey, result, cache_ttl)
    return result


# ---------------------------------------------------------------- normalizer

_TAG_RE = re.compile(r"<[^>]+>")


def _clean(name):
    # Provider sends markup (<b>...</b>) and trailing "~" in some labels.
    return _TAG_RE.sub("", (name or "")).replace("~", "").strip()


def _to_min(t):
    t = (t or "").strip()
    if not t or t == "--" or ":" not in t:
        return None
    try:
        h, m = t.split(":")[:2]
        return int(h) * 60 + int(m)
    except ValueError:
        return None


def _diff_min(sched, actual):
    """Minutes the actual time runs behind the scheduled time (handles midnight wrap)."""
    a, s = _to_min(actual), _to_min(sched)
    if a is None or s is None:
        return 0
    d = a - s
    if d > 720:
        d -= 1440
    elif d < -720:
        d += 1440
    return d


def _dd(t):
    t = (t or "").strip()
    return t if (t and t != "--") else "--:--"


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _parse_server(ts):
    """Provider server clock -> naive IST datetime (times in the payload are IST)."""
    ts = (ts or "").strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=None)
        except ValueError:
            continue
    return None


def _event_dt(s):
    """Actual datetime the train reached/left a stop (arrival preferred; dates are
    more reliable than the provider's departure dates)."""
    d = (s.get("actual_arrival_date") or s.get("actual_departure_date") or "").strip()
    t = s.get("actual_arrival_time")
    if not t or t == "--":
        t = s.get("actual_departure_time")
    t = (t or "").strip()
    if len(d) != 8 or not d.isdigit() or not t or t == "--" or ":" not in t:
        return None
    try:
        return datetime.strptime(d + " " + t[:5], "%Y%m%d %H:%M")
    except ValueError:
        return None


def _fmt_ymd(s):
    s = (s or "").strip()
    if len(s) == 8 and s.isdigit():
        try:
            return datetime.strptime(s, "%Y%m%d").strftime("%d %b %Y")
        except ValueError:
            return s
    return s


def _delay_text(mins):
    mins = mins or 0
    if mins == 0:
        return "On time"
    if mins > 0:
        return f"{mins} min late"
    return f"{abs(mins)} min early"


def _stop(s):
    sched_arr, sched_dep = s.get("arrivalTime"), s.get("departureTime")
    act_arr, act_dep = s.get("actual_arrival_time"), s.get("actual_departure_time")
    delay = _diff_min(sched_arr, act_arr) or _diff_min(sched_dep, act_dep)
    return {
        "code": s.get("stationCode", ""),
        "name": _clean(s.get("stationName")),
        "sched_arr": _dd(sched_arr),
        "sched_dep": _dd(sched_dep),
        "exp_arr": _dd(act_arr),
        "exp_dep": _dd(act_dep),
        "delay": delay,
        "km": _int(s.get("distance")),
        "day": max(0, _int(s.get("dayCount")) - 1),  # day 1 -> +0d, day 2 -> +1d
        "platform": 0,
    }


def normalize_running_status(payload, train_number=None, train_name=None):
    """Turn the provider's payload into a compact shape for the UI.

    Returns a dict with ok=True on success, or {"ok": False, "detail": ...}.
    """
    payload = payload or {}
    body = payload.get("body") or {}
    status = payload.get("status") or {}
    stations = body.get("stations") or []

    ok = (status.get("result") == "success"
          and payload.get("error") in (None, "")
          and stations)
    if not ok:
        msg = ((status.get("message") or {}).get("message")
               or body.get("train_status_message")
               or "Train may not be running for this date.")
        return {"ok": False, "detail": str(msg)}

    src, dst = stations[0], stations[-1]
    server_dt = _parse_server(body.get("server_timestamp"))
    cur_code = body.get("current_station") or src.get("stationCode")

    # Decide which stops the train has already left by comparing each stop's
    # actual time to the provider's server clock. Falls back to the provider's
    # current_station serial if timestamps can't be parsed.
    cur_serial = 1
    for s in stations:
        if s.get("stationCode") == cur_code:
            cur_serial = _int(s.get("stnSerialNumber")) or 1
            break

    crossed, upcoming = [], []
    last_crossed = None
    for s in stations:
        if not s.get("stationCode"):
            continue
        evt = _event_dt(s)
        if server_dt and evt:
            passed = evt <= server_dt
        else:  # no usable timestamp: current station counts as reached
            passed = _int(s.get("stnSerialNumber")) <= cur_serial
        if passed:
            crossed.append(_stop(s))
            last_crossed = s
        else:
            upcoming.append(_stop(s))

    ref = last_crossed or src  # most recent station the train has reached
    delay_min = (_diff_min(ref.get("arrivalTime"), ref.get("actual_arrival_time"))
                 or _diff_min(ref.get("departureTime"), ref.get("actual_departure_time")))

    nxt = upcoming[0] if upcoming else None
    msg = _clean(body.get("train_status_message"))

    return {
        "ok": True,
        "train_number": str(train_number or ""),
        "train_name": train_name or "",
        "source_code": src.get("stationCode"),
        "source_name": _clean(src.get("stationName")),
        "dest_code": dst.get("stationCode"),
        "dest_name": _clean(dst.get("stationName")),
        "start_date": _fmt_ymd(src.get("actual_departure_date")),
        "is_run_day": True,
        "gps_live": True,
        "delay_min": delay_min,
        "delay_text": _delay_text(delay_min),
        "as_of": body.get("time_of_availability", ""),
        "update_time": body.get("server_timestamp", ""),
        "covered_km": _int(ref.get("distance")),
        "total_km": _int(dst.get("distance")),
        "current_station": _clean(ref.get("stationName")),
        "position_lines": [msg] if msg else [],
        "next_station": nxt["name"] if nxt else "",
        "next_in": "",
        "terminated": bool(body.get("terminated")),
        "crossed": crossed,
        "upcoming": upcoming,
    }