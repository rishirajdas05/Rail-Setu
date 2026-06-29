from rest_framework import serializers


class StopPointSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    time = serializers.TimeField(allow_null=True)
    day = serializers.IntegerField()


class TrainResultSerializer(serializers.Serializer):
    number = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    origin = StopPointSerializer()
    destination = StopPointSerializer()
    duration = serializers.CharField(allow_null=True)
    runs_on = serializers.CharField()