"""
Tools the chatbot can call for live RailSetu data.

Each tool maps to an existing RailSetu API. We call them over HTTP on the local
server (AllowAny public endpoints) rather than importing internal functions, so the
tools stay decoupled from view signatures. The schemas below are sent to Groq for
OpenAI-style function calling; execute() runs the chosen tool and returns compact
JSON for the model to phrase.
"""

import requests
from django.conf import settings

BASE = getattr(settings, "SELF_BASE_URL", "http://127.0.0.1:8000")
TIMEOUT = 8


# ---- OpenAI / Groq function schemas ----
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_trains",
            "description": "List trains running between two stations. Use for questions like "
                           "'trains from Delhi to Gwalior'. Origin/destination can be a station "
                           "code (NDLS) or a city name (Delhi).",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "From station code or city name"},
                    "destination": {"type": "string", "description": "To station code or city name"},
                    "date": {"type": "string", "description": "Optional journey date YYYY-MM-DD"},
                },
                "required": ["origin", "destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "seat_availability",
            "description": "Indicative seat availability and fare for a train and class between two "
                           "stations. Use for 'is there availability in 3A on train 12626'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "train_number": {"type": "string"},
                    "origin": {"type": "string", "description": "From station code or city"},
                    "destination": {"type": "string", "description": "To station code or city"},
                    "travel_class": {"type": "string", "description": "1A, 2A, 3A, SL, CC, EC, or 2S"},
                    "quota": {"type": "string", "description": "GN for General or TQ for Tatkal"},
                    "date": {"type": "string", "description": "Optional date YYYY-MM-DD"},
                },
                "required": ["train_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pnr_status",
            "description": "Look up the status of a 10 digit PNR number.",
            "parameters": {
                "type": "object",
                "properties": {"pnr": {"type": "string", "description": "10 digit PNR"}},
                "required": ["pnr"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_confirmation",
            "description": "Estimate the chance a waitlisted ticket confirms, using the machine "
                           "learning model. Use for 'will WL 15 in 3A Tatkal confirm'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "travel_class": {"type": "string", "description": "1A, 2A, 3A, SL, CC, EC, or 2S"},
                    "quota": {"type": "string", "description": "GN or TQ"},
                    "waitlist_position": {"type": "integer"},
                    "days_to_journey": {"type": "integer"},
                },
                "required": ["travel_class", "waitlist_position"],
            },
        },
    },
]


def _get(path, params):
    r = requests.get(f"{BASE}{path}", params=params, timeout=TIMEOUT)
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else {})


def _post(path, body):
    r = requests.post(f"{BASE}{path}", json=body, timeout=TIMEOUT)
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else {})


def _tool_search_trains(args):
    params = {"from": args.get("origin", ""), "to": args.get("destination", "")}
    if args.get("date"):
        params["date"] = args["date"]
    status, data = _get("/api/trains/search/", params)
    if status != 200:
        return {"error": data.get("detail", f"search failed ({status})")}
    results = data.get("results", [])[:8]
    compact = [{
        "number": t.get("number"), "name": t.get("name"), "type": t.get("type"),
        "departs": t.get("origin", {}).get("time"), "arrives": t.get("destination", {}).get("time"),
        "duration": t.get("duration"),
    } for t in results]
    return {"from": data.get("from"), "to": data.get("to"), "count": data.get("count"), "trains": compact}


def _tool_seat_availability(args):
    params = {
        "train": args.get("train_number"),
        "from": args.get("origin", ""), "to": args.get("destination", ""),
        "quota": args.get("quota", "GN"),
    }
    if args.get("date"):
        params["date"] = args["date"]
    if args.get("travel_class"):
        params["cls"] = args["travel_class"]
    status, data = _get("/api/availability/", params)
    if status != 200:
        return {"error": data.get("detail", f"availability failed ({status})")}
    return data


def _tool_pnr_status(args):
    pnr = (args.get("pnr") or "").strip()
    status, data = _get(f"/api/pnr/{pnr}/", {})
    if status != 200:
        return {"error": data.get("detail", f"PNR lookup failed ({status})")}
    return data


def _tool_predict_confirmation(args):
    body = {
        "travel_class": args.get("travel_class"),
        "quota": args.get("quota", "GN"),
        "waitlist_position": args.get("waitlist_position"),
        "days_to_journey": args.get("days_to_journey", 7),
    }
    status, data = _post("/api/predict/confirmation/", body)
    if status != 200:
        return {"error": data.get("detail", f"prediction failed ({status})")}
    return data


_DISPATCH = {
    "search_trains": _tool_search_trains,
    "seat_availability": _tool_seat_availability,
    "pnr_status": _tool_pnr_status,
    "predict_confirmation": _tool_predict_confirmation,
}


def execute(name, args):
    fn = _DISPATCH.get(name)
    if not fn:
        return {"error": f"unknown tool {name}"}
    try:
        return fn(args or {})
    except requests.RequestException:
        return {"error": "could not reach the RailSetu API; is the server running?"}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"tool error: {exc}"}