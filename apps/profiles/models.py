from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from apps.core.models import SoftDeleteModel


class Profile(SoftDeleteModel):
    """ERD `USER` = Django's built-in User (username, email, password hash)
    + this Profile (avatar_url, bio, created_at, is_deleted)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=150, blank=True)
    bio = models.TextField(null=True, blank=True)
    avatar_url = models.URLField(max_length=2048, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return self.user.username

    def delete(self, using=None, keep_parents=False):
        # Soft-deleting a profile also blocks the account from logging in.
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])
        super().restore()
