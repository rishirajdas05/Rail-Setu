from django.contrib import admin

from .models import Station


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "zone", "state")
    search_fields = ("code", "name")
