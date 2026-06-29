"""Background job: evaluate active price/seat alerts.

Run once:        python manage.py check_alerts
Run on a loop:   python manage.py check_alerts --loop 60   (every 60s; Ctrl+C to stop)

On Windows you can schedule the one-shot form with Task Scheduler. The condition
is checked against the same synthetic availability/fare the rest of the app uses,
so a 'seat clears' alert fires when the class currently shows availability and a
'fare drops' alert fires when the current fare is at or below the target.
"""

import time
from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.alerts.models import Alert
from apps.availability import (
    _est_distance, _fare, _journey_hours, _seed, _segment_hours, seat_pool,
)
from apps.trains.models import Train


def _evaluate(alert):
    """Return (pool, fare) for the alert's leg, or None if the train is unknown."""
    train = Train.objects.filter(number=alert.train_number).first()
    if not train:
        return None
    hours = _segment_hours(train, alert.from_code, alert.to_code) or _journey_hours(train) or 2.0
    distance = _est_distance(hours, train.train_type)
    seed = _seed(train.number, alert.journey_date.isoformat(), alert.travel_class, alert.quota)
    pool = seat_pool(seed, alert.travel_class, alert.quota)
    fare = _fare(alert.travel_class, distance, train.train_type, alert.quota)
    return pool, fare


def _seat_label(pool):
    if pool["kind"] == "available":
        return f"AVL {pool['available']}"
    if pool["kind"] == "rac":
        return f"RAC {pool['rac']}"
    return f"WL {pool['waitlist']}"


class Command(BaseCommand):
    help = "Check active price/seat alerts and trigger any whose condition is met."

    def add_arguments(self, parser):
        parser.add_argument("--loop", type=int, default=0,
                            help="Repeat every N seconds instead of running once.")

    def handle(self, *args, **opts):
        loop = opts["loop"]
        while True:
            self._run_once()
            if not loop:
                break
            time.sleep(loop)

    def _run_once(self):
        today = date.today()
        checked = triggered = expired = 0
        for a in Alert.objects.filter(status="active"):
            if a.journey_date < today:
                a.status = "expired"
                a.save(update_fields=["status"])
                expired += 1
                continue
            res = _evaluate(a)
            if not res:
                continue
            pool, fare = res
            checked += 1
            if a.kind == "seat":
                a.last_value = _seat_label(pool)
                met = pool["kind"] == "available"
            else:
                a.last_value = f"\u20b9{fare}"
                met = a.threshold is not None and fare <= a.threshold
            a.last_checked = timezone.now()
            if met:
                a.status = "triggered"
                a.triggered_at = timezone.now()
                triggered += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  hit: {a.user.username} {a.get_kind_display()} "
                    f"{a.train_number}/{a.travel_class} -> {a.last_value}"))
            a.save()
        self.stdout.write(
            f"check_alerts: {checked} checked, {triggered} triggered, {expired} expired "
            f"at {timezone.now():%H:%M:%S}")