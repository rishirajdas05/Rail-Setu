from rest_framework import permissions
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q

from .models import Train
from .serializers import TrainDetailSerializer
from apps.live_client import normalize_running_status, running_status


class TrainSearchView(APIView):
    """GET /api/train-search/?q= — find trains by number or name."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        if len(q) < 2:
            return Response([])
        qs = Train.objects.select_related("source", "destination")
        if q.isdigit():
            qs = qs.filter(number__startswith=q)
        else:
            qs = qs.filter(Q(name__icontains=q) | Q(number__startswith=q))
        out = [{
            "number": t.number,
            "name": t.name,
            "train_type": t.train_type,
            "source_code": t.source_id,
            "source_name": getattr(t.source, "name", ""),
            "destination_code": t.destination_id,
            "destination_name": getattr(t.destination, "name", ""),
        } for t in qs.order_by("number")[:10]]
        return Response(out)


class TrainDetailView(RetrieveAPIView):
    serializer_class = TrainDetailSerializer
    lookup_field = "number"
    lookup_url_kwarg = "number"

    def get_queryset(self):
        return Train.objects.select_related("source", "destination").prefetch_related(
            "stops__station"
        )


def _train_name(number):
    from apps.trains.models import Train
    return (Train.objects.filter(number=str(number))
            .values_list("name", flat=True).first() or "")


class RunningStatusView(APIView):
    """
    GET /api/running-status/<number>/?start_day=1

    Live running status from the configured provider, normalized for the UI.
    Returns 503 when no key is set, so the rest of the app is unaffected.
    """

    def get(self, request, number):
        start_day = request.query_params.get("start_day", "1")
        result = running_status(number, start_day)

        if not result.get("configured"):
            return Response(result, status=503)
        if result.get("error"):
            detail = result.get("detail") or "Could not reach the live provider."
            code = 429 if result.get("error") == "rate_limited" else 502
            return Response({"configured": True, "ok": False, "detail": detail}, status=code)

        norm = normalize_running_status(result.get("data"), number, _train_name(number))
        return Response({"configured": True, **norm}, status=200)


class StationBoardView(APIView):
    """
    GET /api/station-board/?code=GWL&after=HH:MM&limit=40

    Scheduled trains calling at a station, ordered so the next departures from
    'after' (default: now, IST) come first, wrapping around the clock.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from datetime import datetime, time as dtime
        from zoneinfo import ZoneInfo
        from .models import Stop
        from apps.stations.models import Station

        code = (request.query_params.get("code") or "").strip().upper()
        if not code:
            return Response({"detail": "Provide a station code."}, status=400)
        station = Station.objects.filter(code=code).first()
        if not station:
            return Response({"detail": "Station not found."}, status=404)

        try:
            limit = min(int(request.query_params.get("limit", 40)), 100)
        except ValueError:
            limit = 40

        after = request.query_params.get("after")
        ref = None
        if after:
            try:
                ref = datetime.strptime(after[:5], "%H:%M").time()
            except ValueError:
                ref = None
        if ref is None:
            ref = datetime.now(ZoneInfo("Asia/Kolkata")).time()

        stops = (Stop.objects.filter(station_id=code)
                 .select_related("train", "train__source", "train__destination"))

        rows = []
        for st in stops:
            t = st.train
            key = st.departure or st.arrival
            rows.append({
                "number": t.number,
                "name": t.name,
                "type": t.train_type or "",
                "arrival": st.arrival.strftime("%H:%M") if st.arrival else "",
                "departure": st.departure.strftime("%H:%M") if st.departure else "",
                "day_offset": st.day_offset,
                "platform": st.platform or "",
                "distance_km": st.distance_km,
                "source_code": t.source_id,
                "source_name": getattr(t.source, "name", ""),
                "dest_code": t.destination_id,
                "dest_name": getattr(t.destination, "name", ""),
                "_key": key,
            })

        far = dtime(23, 59, 59)
        rows.sort(key=lambda r: r["_key"] or far)
        after_rows = [r for r in rows if r["_key"] and r["_key"] >= ref]
        wrap_rows = [r for r in rows if not r["_key"] or r["_key"] < ref]
        rows = after_rows + wrap_rows
        for r in rows:
            r.pop("_key", None)

        return Response({
            "station": {"code": station.code, "name": station.name,
                        "state": getattr(station, "state", "")},
            "count": len(rows),
            "trains": rows[:limit],
        })