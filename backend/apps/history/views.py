from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import KEEP_PER_KIND, RecentItem
from .serializers import RecentItemSerializer


class RecentView(APIView):
    """GET  /api/recent/   the user's recent trains and searches (newest first)
       POST /api/recent/   record a view/search (idempotent upsert, trimmed)"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        items = RecentItem.objects.filter(user=request.user)
        return Response(RecentItemSerializer(items, many=True).data)

    def post(self, request):
        d = request.data
        kind = (d.get("kind") or "").strip()
        key = (d.get("key") or "").strip()
        if kind not in ("train", "route") or not key:
            return Response({"detail": "kind (train/route) and key are required."}, status=400)

        RecentItem.objects.update_or_create(
            user=request.user, kind=kind, key=key,
            defaults={
                "label": (d.get("label") or key)[:200],
                "subtitle": (d.get("subtitle") or "")[:200],
                "url": (d.get("url") or "")[:300],
            },
        )
        # keep only the newest KEEP_PER_KIND of this kind for this user
        ids = list(
            RecentItem.objects.filter(user=request.user, kind=kind)
            .values_list("id", flat=True)[:KEEP_PER_KIND]
        )
        RecentItem.objects.filter(user=request.user, kind=kind).exclude(id__in=ids).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request):
        RecentItem.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)