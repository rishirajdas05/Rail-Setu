# Railway platform - backend

Django + DRF core API.

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Database + data

```bash
python manage.py migrate
# put stations.json, trains.json, schedules.json in backend/data/ first
python manage.py load_stations
python manage.py load_trains
python manage.py load_schedule
```

Data files are from https://github.com/datameet/railways (CC0). They are not
committed; download them into `backend/data/`.

## Run

```bash
python manage.py createsuperuser
python manage.py runserver
# admin at http://127.0.0.1:8000/admin/
```
