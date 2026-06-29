from rest_framework import serializers

from .models import RecentItem


class RecentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecentItem
        fields = ["id", "kind", "key", "label", "subtitle", "url", "viewed_at"]
        read_only_fields = ["id", "viewed_at"]