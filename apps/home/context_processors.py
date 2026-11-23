from apps.profiles.models import Profile


def nav(request):
    """Gives every page the avatar for the shared nav bar."""
    if not request.user.is_authenticated:
        return {}
    profile = Profile.objects.filter(user=request.user).first()
    return {"nav_avatar": getattr(profile, "avatar_url", None)}
