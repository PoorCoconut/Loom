from django.contrib import admin

from apps.core.admin import SoftDeleteAdmin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(SoftDeleteAdmin):
    list_display = ("user", "full_name", "created_at", "is_deleted")
    search_fields = ("user__username", "user__email", "full_name")
