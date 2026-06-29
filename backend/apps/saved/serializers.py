from rest_framework import serializers

from .models import SavedItem


class SavedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedItem
        fields = ["id", "kind", "key", "label", "subtitle", "url", "created_at"]
        read_only_fields = ["id", "created_at"]