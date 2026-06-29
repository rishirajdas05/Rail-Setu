"""Cancel a booking and compute an IRCTC-style refund.

Charges are a reasonable approximation of Indian Railways rules:
- Confirmed tickets: a flat per-passenger charge if cancelled more than 48 h
  before departure, then 25% (12-48 h), 50% (4-12 h), and no refund inside 4 h.
- RAC/WL tickets: a small clerkage per passenger, the rest refunded.
"""

from datetime import datetime, time

from django.conf import settings
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Booking

# Flat cancellation charge per passenger for a confirmed ticket (> 48 h).
FLAT_CHARGE = {
    "1A": 240, "EC": 240, "2A": 200, "3A": 180,
    "CC": 180, "SL": 120, "2S": 60,
}
CLERKAGE = 60  # per passenger, RAC/WL


def _departure_dt(booking):
    """Best-effort departure datetime from the boarding stop, else 08:00."""
    t = None
    stop = booking.train.stops.filter(station=booking.from_station).first()
    if stop:
        t = stop.departure or stop.arrival
    naive = datetime.combine(booking.journey_date, t or time(8, 0))
    if settings.USE_TZ:
        return timezone.make_aware(naive, timezone.get_current_timezone())
    return naive


def compute_refund(booking, now):
    """Return (charge, refund, rule_text)."""
    fare = float(booking.total_fare or 0)
    npax = booking.passengers.count() or 1
    dep = _departure_dt(booking)
    hours = (dep - now).total_seconds() / 3600.0

    if booking.status in (Booking.Status.WAITLIST, Booking.Status.RAC):
        charge = min(CLERKAGE * npax, fare)
        return charge, fare - charge, f"RAC/WL clerkage (₹{CLERKAGE}/passenger)"

    # Confirmed
    if hours < 4:
        return fare, 0.0, "Within 4 hours of departure — no refund"
    if hours < 12:
        charge = round(fare * 0.5)
        return charge, fare - charge, "50% charge (4–12 h before departure)"
    if hours < 48:
        charge = round(fare * 0.25)
        return charge, fare - charge, "25% charge (12–48 h before departure)"
    per = FLAT_CHARGE.get(booking.travel_class, 180)
    charge = min(per * npax, fare)
    return charge, fare - charge, f"Flat ₹{per}/passenger (more than 48 h before)"


class CancelBookingView(APIView):
    """POST /api/bookings/<pnr>/cancel/ — cancel the caller's own booking."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pnr):
        try:
            booking = (
                Booking.objects
                .select_related("train", "from_station")
                .prefetch_related("passengers", "train__stops")
                .get(pnr=pnr, user=request.user)
            )
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=404)

        if booking.status == Booking.Status.CANCELLED:
            return Response({"detail": "This booking is already cancelled."}, status=400)

        charge, refund, rule = compute_refund(booking, timezone.now())

        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=["status"])
        booking.passengers.update(status=Booking.Status.CANCELLED)

        from .emails import send_booking_cancellation
        sent = send_booking_cancellation(booking, charge, refund, rule)

        return Response({
            "pnr": booking.pnr,
            "status": "CAN",
            "status_display": "Cancelled",
            "total_fare": round(float(booking.total_fare or 0), 2),
            "cancellation_charge": round(charge, 2),
            "refund": round(refund, 2),
            "rule": rule,
            "email_sent_to": booking.user.email if sent else None,
        })