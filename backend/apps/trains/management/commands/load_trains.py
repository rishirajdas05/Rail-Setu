# backend/apps/trains/management/commands/load_trains.py
"""
Load trains from the DataMeet trains.json (GeoJSON FeatureCollection).
Bulk-insert version: fast enough for remote Postgres (Supabase) on deploy.
Stations MUST be loaded first (trains reference station codes via FK).
"""

import json

from django.core.management.base import BaseCommand, CommandError

from apps.stations.models import Station
from apps.trains.models import Train


class Command(BaseCommand):
    help = "Load trains from the DataMeet trains.json file (bulk insert)."

    def add_arguments(self, parser):
        parser.add_argument(
            "json_path", nargs="?", default="data/trains.json",
            help="Path to trains.json (default: data/trains.json)",
        )

    def handle(self, *args, **options):
        path = options["json_path"]
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in {path}: {e}")

        station_codes = set(Station.objects.values_list("code", flat=True))
        if not station_codes:
            raise CommandError("No stations found. Run load_stations first.")

        features = data.get("features", []) if isinstance(data, dict) else data

        objs = {}
        skipped_missing = skipped_bad = 0
        for feat in features:
            props = feat.get("properties", {}) or {}
            number = (props.get("number") or "").strip()
            name = (props.get("name") or "").strip()
            src = (props.get("from_station_code") or "").strip().upper()
            dst = (props.get("to_station_code") or "").strip().upper()

            if not number or not name or len(number) > 20:
                skipped_bad += 1
                continue
            if not src or not dst or src not in station_codes or dst not in station_codes:
                skipped_missing += 1
                continue

            objs[number] = Train(
                number=number,
                name=name,
                train_type=(props.get("type") or "").strip(),
                source_id=src,
                destination_id=dst,
            )

        Train.objects.bulk_create(
            list(objs.values()),
            batch_size=1000,
            ignore_conflicts=True,
        )

        self.stdout.write(self.style.SUCCESS(
            f"Trains done. Inserted {len(objs)}, "
            f"skipped {skipped_missing} (missing station), {skipped_bad} (bad row)."
        ))