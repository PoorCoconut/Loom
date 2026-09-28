from django.conf import settings
from django.db import models


class ReadingSession(models.Model):
    """One reader's playthrough of one story (a save file).

    `user` is nullable so anonymous readers can play too.
    `variable_state` holds the live values, e.g. {"gold": 5, "has_key": true}.
    """

    session_id = models.AutoField(primary_key=True)
    story = models.ForeignKey("stories.Story", on_delete=models.CASCADE, related_name="sessions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="reading_sessions"
    )
    current_node = models.ForeignKey("editor.Node", on_delete=models.PROTECT, related_name="+")
    variable_state = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_played_at = models.DateTimeField(auto_now=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-last_played_at"]

    def __str__(self):
        who = self.user or "anonymous"
        return f"{who} reading {self.story}"
