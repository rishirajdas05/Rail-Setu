from rest_framework import generics, permissions, status
from rest_framework.response import Response

from . import services
from .models import Booking
from .serializers import (
    BookingCreateSerializer,
    BookingSerializer,
    PnrStatusSerializer,
)


class BookingListCreateView(generics.ListCreateAPIView):
    """GET: the current user's bookings. POST: create a booking."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Booking.objects.filter(user=self.request.user)
            .select_related("train", "from_station", "to_station")
            .prefetch_related("passengers")
        )

    def get_serializer_class(self):
        return BookingCreateSerializer if self.request.method == "POST" else BookingSerializer

    def create(self, request, *args, **kwargs):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data

        # A train only offers certain classes (a Shatabdi has CC/EC, not SL/3A).
        from apps.availability import CLASS_BY_TYPE, _STD
        valid_classes = CLASS_BY_TYPE.get(v["train"].train_type, _STD)
        if v["travel_class"] not in valid_classes:
            return Response(
                {"detail": f"Class {v['travel_class']} is not available on train "
                           f"{v['train'].number}. Offered: {', '.join(valid_classes)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            booking = services.create_booking(
                user=request.user,
                train=v["train"],
                from_station=v["from_station"],
                to_station=v["to_station"],
                journey_date=v["journey_date"],
                travel_class=v["travel_class"],
                quota=v["quota"],
                passengers=v["passengers"],
            )
        except services.SeatsUnavailable:
            return Response(
                {"detail": f"Class {v['travel_class']} shows Regret for this date — "
                           f"no seats are available to book. Try another class or date."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .emails import send_booking_confirmation
        sent = send_booking_confirmation(booking)
        data = BookingSerializer(booking).data
        if sent:
            data["email_sent_to"] = booking.user.email
        return Response(data, status=status.HTTP_201_CREATED)

class BookingDetailView(generics.RetrieveAPIView):
    """GET a single booking by PNR (owner only)."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BookingSerializer
    lookup_field = "pnr"

    def get_queryset(self):
        return (
            Booking.objects.filter(user=self.request.user)
            .select_related("train", "from_station", "to_station")
            .prefetch_related("passengers")
        )


class PnrStatusView(generics.RetrieveAPIView):
    """Public PNR status lookup by PNR. No auth, no passenger names."""
    permission_classes = [permissions.AllowAny]
    serializer_class = PnrStatusSerializer
    lookup_field = "pnr"
    queryset = Booking.objects.select_related(
        "train", "from_station", "to_station"
    ).prefetch_related("passengers")