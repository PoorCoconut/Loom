from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SoftDeleteModel


class Node(SoftDeleteModel):
    node_id = models.AutoField(primary_key=True)
    story = models.ForeignKey("stories.Story", on_delete=models.CASCADE, related_name="nodes")
    node_title = models.CharField(max_length=150)
    text_content = models.TextField(blank=True, default="")
    canvas_x = models.IntegerField(default=0)
    canvas_y = models.IntegerField(default=0)
    image_url = models.URLField(max_length=2048, null=True, blank=True)
    audio_url = models.URLField(max_length=2048, null=True, blank=True)

    def __str__(self):
        return self.node_title

    @property
    def is_ending(self):
        return not self.outgoing_paths.exists()


class Path(SoftDeleteModel):
    """A choice connecting one node to another (an edge in the story tree/graph)."""

    path_id = models.AutoField(primary_key=True)
    source_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="outgoing_paths")
    target_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="incoming_paths")
    choice_text = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.source_node} -> {self.target_node}: {self.choice_text}"

    def clean(self):
        if self.source_node_id and self.target_node_id:
            if self.source_node.story_id != self.target_node.story_id:
                raise ValidationError("Both nodes of a path must belong to the same story.")


class GlobalVariable(models.Model):
    """A story-wide variable (e.g. has_key = bool, gold = int) that paths can check or change."""

    class DataType(models.TextChoices):
        INT = "int", "Integer"
        BOOL = "bool", "Boolean"
        STRING = "string", "Text"

    variable_id = models.AutoField(primary_key=True)
    story = models.ForeignKey("stories.Story", on_delete=models.CASCADE, related_name="variables")
    variable_name = models.CharField(max_length=100)
    data_type = models.CharField(max_length=20, choices=DataType.choices, default=DataType.INT)
    default_value = models.CharField(max_length=255, default="0")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["story", "variable_name"], name="uniq_variable_per_story")
        ]

    def __str__(self):
        return f"{self.variable_name} ({self.data_type})"

    def clean(self):
        from .logic import coerce

        try:
            coerce(self.default_value, self.data_type)
        except ValueError as exc:
            raise ValidationError({"default_value": str(exc)})


class PathCondition(SoftDeleteModel):
    """Attached to a Path.

    requirement_type -> the path is only offered if the variable passes this check.
    modifier_type    -> when the path is taken, the variable is changed this way.
    A row may have either one or both.
    """

    class Requirement(models.TextChoices):
        EQ = "eq", "equals"
        NEQ = "neq", "does not equal"
        GT = "gt", "greater than"
        GTE = "gte", "at least"
        LT = "lt", "less than"
        LTE = "lte", "at most"

    class Modifier(models.TextChoices):
        SET = "set", "set to"
        ADD = "add", "add"
        SUBTRACT = "subtract", "subtract"
        TOGGLE = "toggle", "toggle"

    condition_id = models.AutoField(primary_key=True)
    path = models.ForeignKey(Path, on_delete=models.CASCADE, related_name="conditions")
    variable = models.ForeignKey(GlobalVariable, on_delete=models.CASCADE, related_name="conditions")
    requirement_type = models.CharField(max_length=20, choices=Requirement.choices, null=True, blank=True)
    modifier_type = models.CharField(max_length=20, choices=Modifier.choices, null=True, blank=True)
    value = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return f"{self.variable.variable_name} on path {self.path_id}"

    def clean(self):
        from .logic import validate_condition

        validate_condition(self)
