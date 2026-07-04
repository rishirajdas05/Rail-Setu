#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

if [ -f data/stations.json ]; then
  python manage.py load_stations
fi
if [ -f data/trains.json ]; then
  python manage.py load_trains
fi
