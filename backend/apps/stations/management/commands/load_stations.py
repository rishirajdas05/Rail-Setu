# backend/apps/stations/management/commands/load_stations.py
"""
Load stations from the DataMeet stations.json (GeoJSON FeatureCollection).

Usage:
    python manage.py load_stations                 # defaults to data/stations.json
    python manage.py load_stations path/to/file.json

Each GeoJSON feature looks like:
    {
      "geometry": {"type": "Point", "coordinates": [lng, lat]},
      "properties": {"state": "...", "code": "...", "name": "...", "zone": "..."}
    }

Note: GeoJSON coordinates are [longitude, latitude] in that order.
Re-running is safe; existing stations (matched on code) are updated.
"""

import json

from django.core.management.base import BaseCommand, CommandError

from apps.stations.models import Station


class Command(BaseCommand):
    help = "Load stations from the DataMeet stations.json file."

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

        created = updated = skipped = 0
        for feat in features:
            props = feat.get("properties", {}) or {}
            code = (props.get("code") or "").strip().upper()
            name = (props.get("name") or "").strip()
            if not code or not name:
                skipped += 1
                continue

            coords = (feat.get("geometry") or {}).get("coordinates") or [None, None]
            lng, lat = (coords + [None, None])[:2]

            _, was_created = Station.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "zone": (props.get("zone") or "").strip(),
                    "state": (props.get("state") or "").strip(),
                    "latitude": lat,
                    "longitude": lng,
                },
            )
            created += was_created
            updated += not was_created

        self.stdout.write(self.style.SUCCESS(
            f"Stations done. Created {created}, updated {updated}, skipped {skipped}."
        ))
