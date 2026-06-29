from django.db import models


class Event(models.Model):
    """A lightweight usage event for the analytics dashboard.

    kind: 'search', 'predict_confirmation', 'predict_delay', 'predict_rank'
    label: optional detail, e.g. a route "NDLS-GWL" for searches.
    """

    kind = models.CharField(max_length=24, db_index=True)
    label = models.CharField(max_length=80, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind}:{self.label}"


def record(kind, label=""):
    """Best-effort event log. Never raises into the calling request path."""
    try:
        Event.objects.create(kind=str(kind)[:24], label=str(label or "")[:80])
    except Exception:
        pass