"""Guest accounts: temporary, read-only visitors.

A guest is a normal User in the "Guests" group (no migration needed: the group is created on first use).
Guests can browse Discover and read published stories. They cannot create, edit, publish, star or save.
"""

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

GUEST_GROUP = "Guests"
GUEST_PREFIX = "guest_"
GUEST_SESSION_SECONDS = 60 * 60 * 6


def is_guest(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if not hasattr(user, "_is_guest"):
        user._is_guest = user.groups.filter(name=GUEST_GROUP).exists()
    return user._is_guest


def purge_old_guests(hours=24):
    """Throw away guest accounts nobody has used for a while."""
    User = get_user_model()
    User.objects.filter(
        groups__name=GUEST_GROUP, last_login__lt=timezone.now() - timedelta(hours=hours)
    ).delete()


def create_guest():
    from apps.profiles.models import Profile  # imported late: profiles depends on core

    User = get_user_model()
    user = User(username=GUEST_PREFIX + uuid.uuid4().hex[:8])
    user.set_unusable_password()
    user.save()
    group, _ = Group.objects.get_or_create(name=GUEST_GROUP)
    user.groups.add(group)
    Profile.all_objects.get_or_create(user=user, defaults={"full_name": "Guest reader"})
    return user
