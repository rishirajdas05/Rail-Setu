from rest_framework import serializers

from .models import Stop, Train


class StopSerializer(serializers.ModelSerializer):
    station_code = serializers.CharField(source="station_id")
    station_name = serializers.CharField(source="station.name")
    day = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()

    class Meta:
        model = Stop
        fields = [
            "sequence",
            "station_code",
            "station_name",
            "arrival",
            "departure",
            "day",
            "distance_km",
            "platform",
        ]

    def get_day(self, obj):
        return obj.day_offset + 1

    def get_platform(self, obj):
        from .layout import platform_for
        return str(platform_for(obj.train_id, obj.station_id))


class TrainDetailSerializer(serializers.ModelSerializer):

    source_code = serializers.CharField(source="source_id")
    source_name = serializers.CharField(source="source.name")
    destination_code = serializers.CharField(source="destination_id")
    destination_name = serializers.CharField(source="destination.name")
    stops = StopSerializer(many=True, read_only=True)
    coach_layout = serializers.SerializerMethodField()

    class Meta:
        model = Train
        fields = [
            "number",
            "name",
            "train_type",
            "source_code",
            "source_name",
            "destination_code",
            "destination_name",
            "runs_on",
            "stops",
            "coach_layout",
        ]

    def get_coach_layout(self, obj):
        from .layout import coach_layout
        return coach_layout(obj)