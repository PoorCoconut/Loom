from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.user_settings.models import UserSettings

from .models import Profile


@receiver(post_save, sender=User)
def create_user_extras(sender, instance, created, **kwargs):
    """Every new User automatically gets a Profile and UserSettings row."""
    if created:
        Profile.all_objects.get_or_create(user=instance)
        UserSettings.objects.get_or_create(user=instance)
