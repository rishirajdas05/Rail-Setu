from datetime import date

from rest_framework import permissions, status as http
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Alert
from .serializers import AlertSerializer


class AlertListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        items = Alert.objects.filter(user=request.user)
        return Response(AlertSerializer(items, many=True).data)

    def post(self, request):
        d = request.data
        kind = (d.get("kind") or "").strip()
        if kind not in ("seat", "fare"):
            return Response({"detail": "kind must be 'seat' or 'fare'."}, status=400)
        required = ["train_number", "from_code", "to_code", "journey_date", "travel_class"]
        missing = [f for f in required if not str(d.get(f) or "").strip()]
        if missing:
            return Response({"detail": "Missing: " + ", ".join(missing)}, status=400)

        threshold = d.get("threshold")
        if kind == "fare":
            try:
                threshold = int(threshold)
                if threshold <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                return Response({"detail": "A positive target fare is required for a fare alert."}, status=400)
        else:
            threshold = None

        try:
            jd = date.fromisoformat(str(d.get("journey_date")))
        except ValueError:
            return Response({"detail": "journey_date must be YYYY-MM-DD."}, status=400)
        if jd < date.today():
            return Response({"detail": "Pick a journey date in the future."}, status=400)

        alert = Alert.objects.create(
            user=request.user, kind=kind,
            train_number=str(d.get("train_number"))[:16],
            train_name=str(d.get("train_name") or "")[:120],
            from_code=str(d.get("from_code")).upper()[:12],
            to_code=str(d.get("to_code")).upper()[:12],
            journey_date=jd,
            travel_class=str(d.get("travel_class")).upper()[:4],
            quota=str(d.get("quota") or "GN").upper()[:4],
            threshold=threshold,
        )
        return Response(AlertSerializer(alert).data, status=http.HTTP_201_CREATED)


class AlertDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        deleted, _ = Alert.objects.filter(user=request.user, pk=pk).delete()
        if not deleted:
            return Response({"detail": "Not found."}, status=404)
        return Response(status=http.HTTP_204_NO_CONTENT)