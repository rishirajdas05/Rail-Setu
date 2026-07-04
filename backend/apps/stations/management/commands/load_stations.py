# backend/apps/stations/management/commands/load_stations.py
"""
Load stations from the DataMeet stations.json (GeoJSON FeatureCollection).
Bulk-insert version: fast enough for remote Postgres (Supabase) on deploy.

Usage:
    python manage.py load_stations                 # defaults to data/stations.json
    python manage.py load_stations path/to/file.json
"""

import json

from django.core.management.base import BaseCommand, CommandError

from apps.stations.models import Station


class Command(BaseCommand):
    help = "Load stations from the DataMeet stations.json file (bulk insert)."

    def add_arguments(self, parser):
        parser.add_argument(
            "json_path", nargs="?", default="data/stations.json",
            help="Path to stations.json (default: data/stations.json)",
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

        features = data.get("features", []) if isinstance(data, dict) else data

        objs = {}
        skipped = 0
        for feat in features:
            props = feat.get("properties", {}) or {}
            code = (props.get("code") or "").strip().upper()
            name = (props.get("name") or "").strip()
            if not code or not name:
                skipped += 1
                continue

            coords = (feat.get("geometry") or {}).get("coordinates") or [None, None]
            lng, lat = (coords + [None, None])[:2]

            # de-duplicate on code (last one wins), so bulk_create won't hit conflicts
            objs[code] = Station(
                code=code,
                name=name,
                zone=(props.get("zone") or "").strip(),
                state=(props.get("state") or "").strip(),
                latitude=lat,
                longitude=lng,
            )

        Station.objects.bulk_create(
            list(objs.values()),
            batch_size=1000,
            ignore_conflicts=True,
        )

        self.stdout.write(self.style.SUCCESS(
            f"Stations done. Inserted {len(objs)}, skipped {skipped}."
        ))