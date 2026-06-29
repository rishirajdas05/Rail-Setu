from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cities import city_suggestions

from .models import Station
from .serializers import StationSuggestSerializer


class StationSuggestView(APIView):
    """
    GET /api/stations/?q=mum&limit=10

    Autocomplete. Returns matching city groups first (e.g. "Mumbai (all
    stations)"), then stations by code (starts-with) and name (contains).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response([])

        try:
            limit = min(int(request.query_params.get("limit", 10)), 20)
        except ValueError:
            limit = 10

        cities = city_suggestions(q)

        by_code = list(Station.objects.filter(code__istartswith=q)[:limit])
        codes = [s.code for s in by_code]
        remaining = limit - len(by_code)
        by_name = []
        if remaining > 0:
            by_name = list(
                Station.objects.filter(name__icontains=q)
                .exclude(code__in=codes)
                .order_by("name")[:remaining]
            )

        stations = StationSuggestSerializer(by_code + by_name, many=True).data
        return Response((cities + stations)[:limit])