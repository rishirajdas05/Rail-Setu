import datetime

from rest_framework import serializers

from apps.common import Gender, Quota, TravelClass
from apps.stations.models import Station
from apps.trains.models import Stop, Train

from .models import BookedPax, Booking


class PassengerInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    age = serializers.IntegerField(min_value=1, max_value=120)
    gender = serializers.ChoiceField(choices=Gender.choices)


class BookingCreateSerializer(serializers.Serializer):
    train = serializers.CharField()
    from_station = serializers.CharField()
    to_station = serializers.CharField()
    journey_date = serializers.DateField()
    travel_class = serializers.ChoiceField(choices=TravelClass.choices)
    quota = serializers.ChoiceField(choices=Quota.choices, default=Quota.GENERAL)
    passengers = PassengerInputSerializer(many=True)

    def validate_journey_date(self, value):
        if value < datetime.date.today():
            raise serializers.ValidationError("Journey date cannot be in the past.")
        return value

    def validate(self, data):
        if not 1 <= len(data["passengers"]) <= 6:
            raise serializers.ValidationError(
                {"passengers": "A booking must have between 1 and 6 passengers."}
            )

        try:
            train = Train.objects.get(number=str(data["train"]).strip())
        except Train.DoesNotExist:
            raise serializers.ValidationError({"train": "Unknown train number."})

        frm_code = data["from_station"].strip().upper()
        to_code = data["to_station"].strip().upper()
        if frm_code == to_code:
            raise serializers.ValidationError("From and to stations must be different.")

        stations = {
            s.code: s for s in Station.objects.filter(code__in=[frm_code, to_code])
        }
        if frm_code not in stations or to_code not in stations:
            raise serializers.ValidationError("Unknown station code.")

        seqs = dict(
            Stop.objects.filter(
                train=train, station_id__in=[frm_code, to_code]
            ).values_list("station_id", "sequence")
        )
        if frm_code not in seqs or to_code not in seqs:
            raise serializers.ValidationError("This train does not stop at both stations.")
        if seqs[frm_code] >= seqs[to_code]:
            raise serializers.ValidationError("This train does not run in that direction.")

        data["train"] = train
        data["from_station"] = stations[frm_code]
        data["to_station"] = stations[to_code]
        return data


class BookedPaxSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = BookedPax
        fields = ["name", "age", "gender", "coach", "berth",
                  "status", "status_display", "booked_status"]


class BookingSerializer(serializers.ModelSerializer):
    train_number = serializers.CharField(source="train_id")
    train_name = serializers.CharField(source="train.name")
    from_code = serializers.CharField(source="from_station_id")
    to_code = serializers.CharField(source="to_station_id")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    passengers = BookedPaxSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = ["pnr", "train_number", "train_name", "from_code", "to_code",
                  "journey_date", "travel_class", "quota", "status",
                  "status_display", "total_fare", "booked_at", "passengers"]


class PnrStatusSerializer(serializers.ModelSerializer):
    """Public PNR view. Hides passenger names; shows only seat status."""
    train_number = serializers.CharField(source="train_id")
    train_name = serializers.CharField(source="train.name")
    from_code = serializers.CharField(source="from_station_id")
    to_code = serializers.CharField(source="to_station_id")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    passengers = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ["pnr", "train_number", "train_name", "from_code", "to_code",
                  "journey_date", "travel_class", "status", "status_display",
                  "passengers"]

    def get_passengers(self, obj):
        return [
            {
                "passenger": i,
                "status": p.status,
                "status_display": p.get_status_display(),
                "coach": p.coach,
                "berth": p.berth,
                "booked_status": p.booked_status,
            }
            for i, p in enumerate(obj.passengers.all(), start=1)
        ]