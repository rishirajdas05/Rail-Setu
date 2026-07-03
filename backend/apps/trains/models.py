from django.db import models

from apps.common import Quota, TravelClass


class Train(models.Model):
    number = models.CharField(max_length=20, primary_key=True)  # e.g. "12951"
    name = models.CharField(max_length=120)
    train_type = models.CharField(max_length=40, blank=True)
    source = models.ForeignKey(
        "stations.Station", on_delete=models.PROTECT, related_name="trains_from"
    )
    destination = models.ForeignKey(
        "stations.Station", on_delete=models.PROTECT, related_name="trains_to"
    )
    runs_on = models.CharField(max_length=7, default="1111111")  # Mon..Sun flags

    class Meta:
        ordering = ["number"]
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return f"{self.number} {self.name}"


class Stop(models.Model):
    """One row per station a train halts at, ordered by sequence."""
    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name="stops")
    station = models.ForeignKey(
        "stations.Station", on_delete=models.PROTECT, related_name="stops"
    )
    sequence = models.PositiveIntegerField()
    arrival = models.TimeField(null=True, blank=True)
    departure = models.TimeField(null=True, blank=True)
    day_offset = models.PositiveIntegerField(default=0)
    distance_km = models.PositiveIntegerField(default=0)
    platform = models.CharField(max_length=16, blank=True)

    class Meta:
        ordering = ["train", "sequence"]
        constraints = [
            models.UniqueConstraint(fields=["train", "sequence"], name="uniq_train_sequence"),
            models.UniqueConstraint(fields=["train", "station"], name="uniq_train_station"),
        ]
        indexes = [models.Index(fields=["station"])]

    def __str__(self):
        return f"{self.train_id} @ {self.station_id} (#{self.sequence})"


class Fare(models.Model):
    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name="fares")
    travel_class = models.CharField(max_length=2, choices=TravelClass.choices)
    base_fare = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["train", "travel_class"], name="uniq_train_class_fare")
        ]

    def __str__(self):
        return f"{self.train_id} {self.travel_class}: {self.base_fare}"


class Availability(models.Model):
    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name="availability")
    journey_date = models.DateField()
    travel_class = models.CharField(max_length=2, choices=TravelClass.choices)
    quota = models.CharField(max_length=2, choices=Quota.choices, default=Quota.GENERAL)
    available = models.IntegerField(default=0)
    rac = models.IntegerField(default=0)
    waitlist = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "availability"
        constraints = [
            models.UniqueConstraint(
                fields=["train", "journey_date", "travel_class", "quota"],
                name="uniq_availability_slot",
            )
        ]
        indexes = [models.Index(fields=["train", "journey_date"])]

    def __str__(self):
        return f"{self.train_id} {self.journey_date} {self.travel_class}/{self.quota}: {self.available}"
