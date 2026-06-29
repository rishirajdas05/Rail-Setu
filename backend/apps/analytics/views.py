from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.booking.models import Booking

from .models import Event


class AnalyticsView(APIView):
    """GET /api/analytics/  — aggregate stats for the admin dashboard (staff only)."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        bookings = Booking.objects.all()
        total = bookings.count()

        by_status = {row["status"]: row["n"]
                     for row in bookings.values("status").annotate(n=Count("id"))}
        revenue = bookings.exclude(status="CAN").aggregate(s=Sum("total_fare"))["s"] or 0

        top_routes = [
            {"route": f"{r['from_station_id']} → {r['to_station_id']}", "count": r["n"]}
            for r in bookings.values("from_station_id", "to_station_id")
            .annotate(n=Count("id")).order_by("-n")[:8]
        ]
        by_class = [
            {"travel_class": r["travel_class"], "count": r["n"]}
            for r in bookings.values("travel_class").annotate(n=Count("id")).order_by("-n")
        ]

        # bookings per day, last 7 days
        today = timezone.localdate()
        last7 = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            n = bookings.filter(booked_at__date=day).count()
            last7.append({"day": day.strftime("%a %d"), "count": n})

        # searches
        searches = Event.objects.filter(kind="search")
        top_searches = [
            {"route": r["label"].replace("-", " → "), "count": r["n"]}
            for r in searches.exclude(label="").values("label")
            .annotate(n=Count("id")).order_by("-n")[:8]
        ]

        model_usage = [
            {"model": "Confirmation", "count": Event.objects.filter(kind="predict_confirmation").count()},
            {"model": "Delay", "count": Event.objects.filter(kind="predict_delay").count()},
            {"model": "Ranking", "count": Event.objects.filter(kind="predict_rank").count()},
        ]

        return Response({
            "bookings": {
                "total": total,
                "confirmed": by_status.get("CNF", 0),
                "rac": by_status.get("RAC", 0),
                "waitlisted": by_status.get("WL", 0),
                "cancelled": by_status.get("CAN", 0),
                "revenue": float(revenue),
                "top_routes": top_routes,
                "by_class": by_class,
                "last7": last7,
            },
            "searches": {"total": searches.count(), "top": top_searches},
            "model_usage": model_usage,
        })