from django.contrib.auth.models import User
from django.db import models


class RecentItem(models.Model):
    """A per-user recently-viewed train or recent search, kept newest-first.

    kind 'train' -> a viewed train; kind 'route' -> a run search.
    Upserted on (user, kind, key); only the latest few per kind are kept.
    """

    KIND = [("train", "Train"), ("route", "Route")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recent_items")
    kind = models.CharField(max_length=8, choices=KIND)
    key = models.CharField(max_length=80)
    label = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True, default="")
    url = models.CharField(max_length=300)
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "kind", "key")
        ordering = ["-viewed_at"]

    def __str__(self):
        return f"{self.user_id}:{self.kind}:{self.key}"


KEEP_PER_KIND = 8