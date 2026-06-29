from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("kind", "label", "created_at")
    list_filter = ("kind",)
    search_fields = ("label",)