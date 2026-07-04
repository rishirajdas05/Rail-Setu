from django.db import models


class Station(models.Model):
    code = models.CharField(max_length=20, primary_key=True)   # e.g. "NDLS"
    name = models.CharField(max_length=120)
    zone = models.CharField(max_length=20, blank=True)
    state = models.CharField(max_length=60, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return f"{self.name} ({self.code})"