#!/usr/bin/env bash
# Render build for the Django web service. Runs from the backend/ root.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Seed reference data once. Postgres persists between deploys, so we only import
# when a table is empty, and only if the JSON file is present in the repo.
row_exists () {  # exit 0 if the model already has rows
  python manage.py shell -c "import sys; from $1 import $2; sys.exit(0 if $2.objects.exists() else 1)"
}

if [ -f data/stations.json ]; then
  row_exists apps.stations.models Station || python manage.py load_stations
fi
if [ -f data/trains.json ]; then
  row_exists apps.trains.models Train || python manage.py load_trains
fi
if [ -f data/schedules.json ]; then
  row_exists apps.trains.models Stop || python manage.py load_schedule
fi