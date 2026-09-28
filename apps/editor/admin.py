from django.contrib import admin

from apps.core.admin import SoftDeleteAdmin, SoftDeleteInline

from .models import GlobalVariable, Node, Path, PathCondition


class PathConditionInline(SoftDeleteInline):
    model = PathCondition


class OutgoingPathInline(SoftDeleteInline):
    model = Path
    fk_name = "source_node"


@admin.register(Node)
class NodeAdmin(SoftDeleteAdmin):
    list_display = ("node_title", "story", "canvas_x", "canvas_y", "is_deleted")
    list_filter = ("story", "is_deleted")
    search_fields = ("node_title", "text_content")
    inlines = [OutgoingPathInline]


@admin.register(Path)
class PathAdmin(SoftDeleteAdmin):
    list_display = ("choice_text", "source_node", "target_node", "is_deleted")
    inlines = [PathConditionInline]


@admin.register(GlobalVariable)
class GlobalVariableAdmin(admin.ModelAdmin):
    list_display = ("variable_name", "story", "data_type", "default_value")
    list_filter = ("story",)


@admin.register(PathCondition)
class PathConditionAdmin(SoftDeleteAdmin):
    list_display = ("path", "variable", "requirement_type", "modifier_type", "value", "is_deleted")
