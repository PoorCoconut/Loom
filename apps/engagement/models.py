from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import SoftDeleteModel


class Review(SoftDeleteModel):
    review_id = models.AutoField(primary_key=True)
    story = models.ForeignKey("stories.Story", on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name="review_rating_1_to_5"),
            # one live review per user per story (a soft-deleted one doesn't block a new one)
            models.UniqueConstraint(
                fields=["story", "user"], condition=models.Q(is_deleted=False), name="uniq_live_review_per_user"
            ),
        ]

    def __str__(self):
        return f"{self.user} rated {self.story} {self.rating}/5"


class StoryLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="story_likes")
    story = models.ForeignKey("stories.Story", on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "story"], name="uniq_story_like")]

    def __str__(self):
        return f"{self.user} likes {self.story}"


class StoryFavourite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="story_favourites")
    story = models.ForeignKey("stories.Story", on_delete=models.CASCADE, related_name="favourites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "story"], name="uniq_story_favourite")]

    def __str__(self):
        return f"{self.user} favourited {self.story}"
