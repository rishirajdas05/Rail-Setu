"""Deterministic running-days pattern per train.

Honest note: the static dataset stores runs_on as "1111111" (daily) for every
train, so true weekly/daily schedules are not available offline; only the live
API has them. To make day-of-week filtering work and be demonstrable, we derive
a STABLE pseudo-schedule from the train number: about two thirds of trains run
daily, the rest on a fixed subset of days. The same train always yields the same
pattern. This is simulated and labelled as such in the UI.

Pattern is a 7-char string for Mon..Sun, e.g. "1010100".
"""

import hashlib


def _hash(number) -> int:
    return int(hashlib.md5(str(number).encode()).hexdigest()[:8], 16)


def effective_runs_on(number) -> str:
    h = _hash(number)
    # ~65% of trains run daily
    if h % 100 < 65:
        return "1111111"
    # the rest run on 2-5 fixed days
    ndays = 2 + (h >> 7) % 4
    bits = ["0"] * 7
    for i in range(ndays):
        bits[(h >> (3 * i)) % 7] = "1"
    if bits.count("1") < 2:
        bits[h % 7] = "1"
        bits[(h // 7) % 7] = "1"
    return "".join(bits)


def runs_on_date(number, journey_date) -> bool:
    """True if the train runs on the given date's weekday."""
    return effective_runs_on(number)[journey_date.weekday()] == "1"