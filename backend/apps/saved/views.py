from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SavedItem
from .serializers import SavedItemSerializer


class SavedListCreateView(APIView):
    """GET  /api/saved/        list the user's saved trains and routes
       POST /api/saved/        save one (idempotent on kind+key)"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        items = SavedItem.objects.filter(user=request.user)
        return Response(SavedItemSerializer(items, many=True).data)

    def post(self, request):
        data = request.data
        kind = (data.get("kind") or "").strip()
        key = (data.get("key") or "").strip()
        if kind not in ("train", "route") or not key:
            return Response({"detail": "kind (train/route) and key are required."}, status=400)
        item, created = SavedItem.objects.get_or_create(
            user=request.user, kind=kind, key=key,
            defaults={
                "label": (data.get("label") or key)[:200],
                "subtitle": (data.get("subtitle") or "")[:200],
                "url": (data.get("url") or "")[:300],
            },
        )
        return Response(
            SavedItemSerializer(item).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SavedDeleteView(APIView):
    """DELETE /api/saved/<pk>/   remove one of the user's saved items"""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        deleted, _ = SavedItem.objects.filter(user=request.user, pk=pk).delete()
        if not deleted:
            return Response({"detail": "Not found."}, status=404)
        return Response(status=status.HTTP_204_NO_CONTENT)