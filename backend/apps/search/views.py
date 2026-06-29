from datetime import datetime

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cities import candidate_codes_for, expand_token
from apps.stations.models import Station

from .serializers import TrainResultSerializer
from .services import search_trains


class TrainSearchView(APIView):
    """
    GET /api/trains/search/?from=GWL&to=MUMBAI&date=2026-06-20

    'from' and 'to' may be a station code (e.g. GWL) or a city name
    (e.g. MUMBAI), which expands to all of that city's terminals.
    """

    def get(self, request):
        raw_from = request.query_params.get("from", "").strip().upper()
        raw_to = request.query_params.get("to", "").strip().upper()
        date_str = request.query_params.get("date", "").strip()

        if not raw_from or not raw_to:
            return Response(
                {"detail": "Both 'from' and 'to' query parameters are required."},
                status=400,
            )

        candidates = candidate_codes_for(raw_from) | candidate_codes_for(raw_to)
        existing = set(
            Station.objects.filter(code__in=candidates).values_list("code", flat=True)
        )
        from_codes = expand_token(raw_from, existing)
        to_codes = expand_token(raw_to, existing)

        missing = []
        if from_codes is None:
            missing.append(raw_from)
        if to_codes is None:
            missing.append(raw_to)
        if missing:
            return Response(
                {"detail": f"Unknown station or city: {', '.join(missing)}"}, status=404
            )
        if set(from_codes) & set(to_codes):
            return Response(
                {"detail": "'from' and 'to' must be different places."}, status=400
            )

        journey_date = None
        if date_str:
            try:
                journey_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"detail": "date must be in YYYY-MM-DD format."}, status=400
                )

        results = search_trains(from_codes, to_codes, journey_date)
        data = TrainResultSerializer(results, many=True).data

        from apps.analytics.models import record
        record("search", f"{raw_from}-{raw_to}")
        return Response({
            "from": raw_from,
            "to": raw_to,
            "date": date_str or None,
            "count": len(data),
            "results": data,
        })