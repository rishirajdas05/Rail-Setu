"""
City groups: map a metro to all of its terminal stations so a search for
"Mumbai" matches trains arriving at CST, LTT, Dadar, Panvel, etc.

Codes that are not present in the loaded dataset are simply ignored at
search time, so this list can be broader than any single data snapshot.
"""

CITY_GROUPS = {
    "DELHI": {
        "label": "Delhi (all stations)",
        "stations": ["NDLS", "DLI", "NZM", "ANVT", "DEE", "DSA", "SZM"],
    },
    "MUMBAI": {
        "label": "Mumbai (all stations)",
        "stations": ["CSTM", "LTT", "DR", "BDTS", "PNVL", "BCT", "KYN"],
    },
    "KOLKATA": {
        "label": "Kolkata (all stations)",
        "stations": ["HWH", "SDAH", "KOAA", "SRC", "SHM"],
    },
    "CHENNAI": {
        "label": "Chennai (all stations)",
        "stations": ["MAS", "MS", "MSB"],
    },
    "BENGALURU": {
        "label": "Bengaluru (all stations)",
        "stations": ["SBC", "YPR", "BNC", "KJM"],
    },
    "HYDERABAD": {
        "label": "Hyderabad (all stations)",
        "stations": ["HYB", "SC", "KCG"],
    },
}

# Typed names that should resolve to a city group.
CITY_ALIASES = {
    "BOMBAY": "MUMBAI",
    "BANGALORE": "BENGALURU",
    "CALCUTTA": "KOLKATA",
    "MADRAS": "CHENNAI",
}


def city_suggestions(q):
    """City options for the autocomplete, matched by name prefix."""
    q = q.strip().lower()
    out = []
    for key, group in CITY_GROUPS.items():
        if key.lower().startswith(q) or group["label"].lower().startswith(q):
            out.append({"code": key, "name": group["label"], "state": "City", "is_city": True})
    for alias, key in CITY_ALIASES.items():
        if alias.lower().startswith(q):
            group = CITY_GROUPS[key]
            out.append({"code": key, "name": group["label"], "state": "City", "is_city": True})
    return out


def candidate_codes_for(token):
    """Every station code a token might resolve to (for an existence check)."""
    token = token.strip().upper()
    key = CITY_ALIASES.get(token, token)
    if key in CITY_GROUPS:
        return set(CITY_GROUPS[key]["stations"])
    return {token}


def expand_token(token, valid_codes):
    """
    Resolve a search token to a list of real station codes.
    Returns None if it is neither a known city nor a known station.
    """
    token = token.strip().upper()
    key = CITY_ALIASES.get(token, token)
    if key in CITY_GROUPS:
        codes = [c for c in CITY_GROUPS[key]["stations"] if c in valid_codes]
        return codes or None
    if token in valid_codes:
        return [token]
    return None