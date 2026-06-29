from django.contrib.auth.models import User
from django.db import models


class Alert(models.Model):
    """A user's price or seat alert for a specific train + leg + date + class.

    A background job (manage.py check_alerts) evaluates active alerts against the
    current (synthetic) availability/fare and flips them to 'triggered' when the
    condition is met.
    """

    KIND = [("seat", "Seat clears"), ("fare", "Fare drops")]
    STATUS = [("active", "Active"), ("triggered", "Triggered"), ("expired", "Expired")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="alerts")
    kind = models.CharField(max_length=8, choices=KIND)

    train_number = models.CharField(max_length=16)
    train_name = models.CharField(max_length=120, blank=True, default="")
    from_code = models.CharField(max_length=12)
    to_code = models.CharField(max_length=12)
    journey_date = models.DateField()
    travel_class = models.CharField(max_length=4)
    quota = models.CharField(max_length=4, default="GN")

    threshold = models.IntegerField(null=True, blank=True)  # target fare (rupees) for fare alerts

    status = models.CharField(max_length=10, choices=STATUS, default="active")
    last_value = models.CharField(max_length=40, blank=True, default="")
    last_checked = models.DateTimeField(null=True, blank=True)
    triggered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id}:{self.kind}:{self.train_number}/{self.travel_class}"