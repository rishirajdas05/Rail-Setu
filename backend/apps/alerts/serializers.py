from rest_framework import serializers

from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            "id", "kind", "train_number", "train_name", "from_code", "to_code",
            "journey_date", "travel_class", "quota", "threshold",
            "status", "last_value", "last_checked", "triggered_at", "created_at",
        ]
        read_only_fields = ["id", "status", "last_value", "last_checked", "triggered_at", "created_at"]