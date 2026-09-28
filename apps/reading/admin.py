from django.contrib import admin

from .models import ReadingSession


@admin.register(ReadingSession)
class ReadingSessionAdmin(admin.ModelAdmin):
    list_display = ("story", "user", "current_node", "is_completed", "last_played_at")
    list_filter = ("is_completed",)
