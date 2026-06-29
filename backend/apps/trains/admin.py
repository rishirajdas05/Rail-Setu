from django.contrib import admin

from .models import Availability, Fare, Stop, Train


@admin.register(Train)
class TrainAdmin(admin.ModelAdmin):
    list_display = ("number", "name", "train_type", "source", "destination")
    search_fields = ("number", "name")
    list_filter = ("train_type",)


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ("train", "sequence", "station", "arrival", "departure", "day_offset")
    search_fields = ("train__number", "station__code")


admin.site.register(Fare)
admin.site.register(Availability)
