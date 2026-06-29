# backend/apps/trains/management/commands/load_schedule.py
"""
Load the train schedule (stops) from the DataMeet schedules.json.

Usage:
    python manage.py load_schedule                 # defaults to data/schedules.json
    python manage.py load_schedule path/to/file.json

This is the big file (~417k records). Each record ties a train to a station:
    {
      "arrival": "07:55:00" | "None",
      "departure": "07:55:00" | "None",
      "day": 1,
      "station_code": "FM",
      "train_number": "47154"
    }

The source data has no explicit stop order, so stops for each train are sorted
by (day, time) and assigned a sequence starting at 1. Trains and stations must
already be loaded; records pointing at a missing train or station are skipped.

The whole Stop table is rebuilt on each run so reloading is idempotent. Inserts
are batched to keep memory and query counts sane.
"""

import json
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.stations.models import Station
from apps.trains.models import Stop, Train

BATCH_SIZE = 5000


def parse_time(value):
    """Return a time object, or None for 'None' / blank / unparseable values."""
    value = (value or "").strip()
    if not value or value.lower() == "none":
        return None
    try:
        return datetime.strptime(value, "%H:%M:%S").time()
    except ValueError:
        return None


def sort_key(record):
    """Order a train's stops along its route: by day, then by clock time."""
    day = record.get("day") or 1
    t = parse_time(record.get("arrival")) or parse_time(record.get("departure"))
    # Origin has no arrival; terminus has no departure. Push timeless rows last
    # within their day so they do not jump ahead of timed stops.
    return (day, t is None, t or datetime.min.time())


class Command(BaseCommand):
    help = "Load the train schedule (stops) from the DataMeet schedules.json file."

    def add_arguments(self, parser):
        parser.add_argument(
            "json_path", nargs="?", default="data/schedules.json",
            help="Path to schedules.json (default: data/schedules.json)",
        )

    def handle(self, *args, **options):
        path = options["json_path"]
        try:
            with open(path, encoding="utf-8") as f:
                records = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in {path}: {e}")

        train_numbers = set(Train.objects.values_list("number", flat=True))
        station_codes = set(Station.objects.values_list("code", flat=True))
        if not train_numbers or not station_codes:
            raise CommandError("Load stations and trains before the schedule.")

        # Group valid records by train so we can assign a per-train sequence.
        by_train = {}
        skipped = 0
        for r in records:
            tn = (r.get("train_number") or "").strip()
            sc = (r.get("station_code") or "").strip().upper()
            if tn not in train_numbers or sc not in station_codes:
                skipped += 1
                continue
            r["station_code"] = sc
            by_train.setdefault(tn, []).append(r)

        del records  # free the big parsed list before building Stop objects

        created = 0
        with transaction.atomic():
            Stop.objects.all().delete()  # full rebuild for idempotent reloads

            batch = []
            for tn, stops in by_train.items():
                stops.sort(key=sort_key)
                for seq, r in enumerate(stops, start=1):
                    batch.append(Stop(
                        train_id=tn,
                        station_id=r["station_code"],
                        sequence=seq,
                        arrival=parse_time(r.get("arrival")),
                        departure=parse_time(r.get("departure")),
                        day_offset=max((r.get("day") or 1) - 1, 0),
                    ))
                    if len(batch) >= BATCH_SIZE:
                        # ignore_conflicts guards against a train listing the same
                        # station twice (loops/reversals exist in the real data).
                        Stop.objects.bulk_create(batch, ignore_conflicts=True)
                        created += len(batch)
                        batch = []
            if batch:
                Stop.objects.bulk_create(batch, ignore_conflicts=True)
                created += len(batch)

        self.stdout.write(self.style.SUCCESS(
            f"Schedule done. Inserted ~{created} stops across {len(by_train)} trains, "
            f"skipped {skipped} (missing train or station)."
        ))
