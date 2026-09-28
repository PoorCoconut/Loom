from django.contrib import admin


class SoftDeleteAdmin(admin.ModelAdmin):
    """Admin that can see (and restore) soft-deleted rows."""

    list_filter = ("is_deleted",)
    actions = ["restore_selected"]

    def get_queryset(self, request):
        qs = self.model.all_objects.get_queryset()
        ordering = self.get_ordering(request)
        return qs.order_by(*ordering) if ordering else qs

    @admin.action(description="Restore selected (undo soft delete)")
    def restore_selected(self, request, queryset):
        queryset.update(is_deleted=False)


class SoftDeleteInline(admin.TabularInline):
    extra = 0

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset()
