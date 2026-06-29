from django.contrib.auth.models import User
from django.db import models


class SavedItem(models.Model):
    """A train or route a user has saved for quick access."""

    KIND_CHOICES = [("train", "Train"), ("route", "Route")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_items")
    kind = models.CharField(max_length=8, choices=KIND_CHOICES)
    key = models.CharField(max_length=80)          # train number, or "NDLS-GWL"
    label = models.CharField(max_length=200)        # display title
    subtitle = models.CharField(max_length=200, blank=True, default="")
    url = models.CharField(max_length=300)          # where clicking it goes
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "kind", "key")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id}:{self.kind}:{self.key}"