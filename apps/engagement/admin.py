from django.contrib import admin

from apps.core.admin import SoftDeleteAdmin

from .models import Review, StoryFavourite, StoryLike


@admin.register(Review)
class ReviewAdmin(SoftDeleteAdmin):
    list_display = ("story", "user", "rating", "created_at", "is_deleted")
    list_filter = ("rating", "is_deleted")


admin.site.register(StoryLike)
admin.site.register(StoryFavourite)
