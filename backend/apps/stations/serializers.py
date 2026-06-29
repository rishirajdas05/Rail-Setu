from rest_framework import serializers

from .models import Station


class StationSuggestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ["code", "name", "state"]