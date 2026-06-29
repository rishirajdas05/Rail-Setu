import random

from django.conf import settings
from django.db import models

from apps.common import Gender, Quota, TravelClass


def generate_pnr():
    """10 digit PNR. Uniqueness enforced at the DB level on Booking.pnr."""
    return "".join(random.choices("0123456789", k=10))


class Passenger(models.Model):
    """A traveller saved to a user's profile for quick reuse."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_passengers"
    )
    name = models.CharField(max_length=80)
    age = models.PositiveSmallIntegerField()
    gender = models.CharField(max_length=1, choices=Gender.choices)

    def __str__(self):
        return f"{self.name} ({self.age})"


class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "CNF", "Confirmed"
        RAC = "RAC", "Reservation Against Cancellation"
        WAITLIST = "WL", "Waitlisted"
        CANCELLED = "CAN", "Cancelled"

    pnr = models.CharField(max_length=10, unique=True, default=generate_pnr, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings"
    )
    train = models.ForeignKey("trains.Train", on_delete=models.PROTECT, related_name="bookings")
    from_station = models.ForeignKey(
        "stations.Station", on_delete=models.PROTECT, related_name="bookings_from"
    )
    to_station = models.ForeignKey(
        "stations.Station", on_delete=models.PROTECT, related_name="bookings_to"
    )
    journey_date = models.DateField()
    travel_class = models.CharField(max_length=2, choices=TravelClass.choices)
    quota = models.CharField(max_length=2, choices=Quota.choices, default=Quota.GENERAL)
    status = models.CharField(max_length=3, choices=Status.choices, default=Status.WAITLIST)
    total_fare = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    booked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-booked_at"]
        indexes = [
            models.Index(fields=["pnr"]),
            models.Index(fields=["user", "-booked_at"]),
        ]

    def __str__(self):
        return f"PNR {self.pnr} ({self.status})"


class BookedPax(models.Model):
    """One row per traveller on a booking, each with its own seat and status."""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="passengers")
    name = models.CharField(max_length=80)
    age = models.PositiveSmallIntegerField()
    gender = models.CharField(max_length=1, choices=Gender.choices)
    coach = models.CharField(max_length=10, blank=True)
    berth = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=3, choices=Booking.Status.choices, default=Booking.Status.WAITLIST
    )
    booked_status = models.CharField(max_length=12, blank=True)

    def __str__(self):
        return f"{self.name} - {self.status}"
