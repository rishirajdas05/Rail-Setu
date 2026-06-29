"""Seat allocation and booking creation.

Status, seat pool, berth and fare are all derived from the SAME synthetic
availability the train page shows (apps.availability), so a class that displays
Regret cannot be booked, a WL class produces a WL ticket, and confirmed berths
vary by train/date instead of always being seat 1.
"""

from decimal import Decimal

from django.db import transaction

from apps.availability import (_est_distance, _fare, _journey_hours, _seed,
                               _segment_hours, seat_pool)
from apps.trains.models import Availability

from .models import BookedPax, Booking

COACH_PREFIX = {"1A": "H", "2A": "A", "3A": "B", "SL": "S", "CC": "C", "2S": "D", "EC": "E"}
BERTHS_PER_COACH = {"1A": 24, "2A": 46, "3A": 64, "SL": 72, "CC": 78, "2S": 108, "EC": 56}
SLEEPER_PATTERN = ["LB", "MB", "UB", "LB", "MB", "UB", "SL", "SU"]

_SEVERITY = {
    Booking.Status.WAITLIST: 0,
    Booking.Status.RAC: 1,
    Booking.Status.CONFIRMED: 2,
}


class SeatsUnavailable(Exception):
    """Raised when a class shows Regret and cannot be booked."""

    def __init__(self, travel_class):
        self.travel_class = travel_class
        super().__init__(f"No seats available (Regret) in {travel_class}.")


def _berth_label(travel_class, seat_no):
    """Map a confirmed seat number to a coach and berth like ('S2', '34 UB')."""
    prefix = COACH_PREFIX.get(travel_class, "S")
    per = BERTHS_PER_COACH.get(travel_class, 72)
    coach = f"{prefix}{(seat_no - 1) // per + 1}"
    pos = (seat_no - 1) % per + 1
    if travel_class in ("SL", "3A", "2A", "1A"):
        return coach, f"{pos} {SLEEPER_PATTERN[(pos - 1) % 8]}"
    return coach, str(pos)


@transaction.atomic
def create_booking(*, user, train, from_station, to_station, journey_date,
                   travel_class, quota, passengers):
    """Allocate seats and persist the booking atomically.

    The initial pool (confirmed / RAC / waitlist) is seeded from the displayed
    availability for this train+date+class+quota. Passengers fill confirmed
    berths first, then RAC, then waitlist. The booking's overall status is the
    least confirmed status among its passengers.
    """
    seed = _seed(train.number, journey_date.isoformat(), travel_class, quota)
    pool = seat_pool(seed, travel_class, quota)
    if pool["kind"] == "regret":
        raise SeatsUnavailable(travel_class)

    conf_total = pool["available"]
    rac_total = pool["rac"]

    # Lock the availability row (real locking on PostgreSQL; harmless on SQLite).
    locked = Availability.objects.select_for_update()
    try:
        avail = locked.get(
            train=train, journey_date=journey_date,
            travel_class=travel_class, quota=quota,
        )
    except Availability.DoesNotExist:
        Availability.objects.create(
            train=train, journey_date=journey_date, travel_class=travel_class,
            quota=quota, available=conf_total, rac=rac_total,
            waitlist=pool["waitlist"],
        )
        avail = locked.get(
            train=train, journey_date=journey_date,
            travel_class=travel_class, quota=quota,
        )

    booking = Booking.objects.create(
        user=user, train=train, from_station=from_station, to_station=to_station,
        journey_date=journey_date, travel_class=travel_class, quota=quota,
        status=Booking.Status.WAITLIST, total_fare=0,
    )

    # Vary the starting berth by slot so it isn't always seat 1.
    per = BERTHS_PER_COACH.get(travel_class, 72)
    base_seat = (seed % (per * 4)) + 1
    rac_base = (seed >> 6) % 40 + 1
    conf_i = 0

    pax_objs, statuses = [], []
    for p in passengers:
        if avail.available > 0:
            seat_no = base_seat + conf_i
            conf_i += 1
            coach, berth = _berth_label(travel_class, seat_no)
            avail.available -= 1
            st = Booking.Status.CONFIRMED
            booked_status = f"CNF/{coach}/{berth}"
        elif avail.rac > 0:
            rac_no = rac_base + (rac_total - avail.rac)
            avail.rac -= 1
            st = Booking.Status.RAC
            coach, berth = "", ""
            booked_status = f"RAC {rac_no}"
        else:
            avail.waitlist += 1
            st = Booking.Status.WAITLIST
            coach, berth = "", ""
            booked_status = f"WL/{avail.waitlist}"

        statuses.append(st)
        pax_objs.append(BookedPax(
            booking=booking, name=p["name"], age=p["age"], gender=p["gender"],
            coach=coach, berth=berth, status=st, booked_status=booked_status,
        ))

    BookedPax.objects.bulk_create(pax_objs)
    avail.save(update_fields=["available", "rac", "waitlist"])

    # Fare consistent with the train page (per-segment, per-km, with quota).
    seg = _segment_hours(train, from_station.pk, to_station.pk)
    hours = seg or _journey_hours(train)
    distance = _est_distance(hours, train.train_type)
    fare_each = _fare(travel_class, distance, train.train_type, quota)

    booking.status = min(statuses, key=lambda s: _SEVERITY[s])
    booking.total_fare = Decimal(str(fare_each)) * len(passengers)
    booking.save(update_fields=["status", "total_fare"])
    return booking