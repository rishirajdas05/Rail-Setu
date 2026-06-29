from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "train_number", "travel_class", "status", "last_value", "last_checked")
    list_filter = ("kind", "status")
    search_fields = ("train_number", "user__username")
