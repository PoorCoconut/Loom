from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import SoftDeleteModel


class Tag(models.Model):
    tag_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Story(SoftDeleteModel):
    story_id = models.AutoField(primary_key=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="authored_stories"
    )
    # Circular reference (Node.story -> Story, Story.starting_node -> Node), hence the string.
    starting_node = models.ForeignKey(
        "editor.Node", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    title = models.CharField(max_length=150)
    synopsis = models.TextField(null=True, blank=True)
    cover_image_url = models.URLField(max_length=2048, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_modified_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    tags = models.ManyToManyField(Tag, through="StoryTag", related_name="stories", blank=True)
    collaborators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="StoryCollaborator",
        related_name="collaborating_stories",
        blank=True,
    )

    class Meta:
        verbose_name_plural = "stories"
        ordering = ["-last_modified_at"]

    def __str__(self):
        return self.title

    def clean(self):
        if self.starting_node_id and self.starting_node.story_id != self.pk:
            raise ValidationError({"starting_node": "The starting node must belong to this story."})

    def publish(self):
        if not self.starting_node_id:
            raise ValidationError("Set a starting node before publishing.")
        self.is_published = True
        self.published_at = self.published_at or timezone.now()
        self.save(update_fields=["is_published", "published_at", "last_modified_at"])

    def unpublish(self):
        self.is_published = False
        self.save(update_fields=["is_published", "last_modified_at"])


class StoryTag(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["story", "tag"], name="uniq_story_tag")]

    def __str__(self):
        return f"{self.story} #{self.tag}"


class StoryCollaborator(models.Model):
    class Role(models.TextChoices):
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"

    story = models.ForeignKey(Story, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EDITOR)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["story", "user"], name="uniq_story_collaborator")
        ]

    def clean(self):
        if self.story_id and self.user_id == self.story.author_id:
            raise ValidationError("The author is already the owner of this story.")

    def __str__(self):
        return f"{self.user} -> {self.story} ({self.role})"
