from django.contrib import admin

from .models import SavedItem


@admin.register(SavedItem)
class SavedItemAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "key", "label", "created_at")
    list_filter = ("kind",)
    search_fields = ("key", "label", "user__username")