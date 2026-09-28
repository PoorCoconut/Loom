from django.contrib import admin

from apps.core.admin import SoftDeleteAdmin

from .models import Story, StoryCollaborator, StoryTag, Tag


class StoryTagInline(admin.TabularInline):
    model = StoryTag
    extra = 0


class CollaboratorInline(admin.TabularInline):
    model = StoryCollaborator
    extra = 0


@admin.register(Story)
class StoryAdmin(SoftDeleteAdmin):
    list_display = ("title", "author", "is_published", "last_modified_at", "is_deleted")
    list_filter = ("is_published", "is_deleted")
    search_fields = ("title", "author__username")
    inlines = [StoryTagInline, CollaboratorInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "starting_node":
            # Only show nodes of the story being edited.
            obj_id = request.resolver_match.kwargs.get("object_id")
            from apps.editor.models import Node
            kwargs["queryset"] = Node.objects.filter(story_id=obj_id) if obj_id else Node.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Tag)
