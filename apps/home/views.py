from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.profiles.models import Profile
from apps.stories.models import Story


def _my_stories(user):
    return Story.objects.filter(Q(author=user) | Q(collaborators=user)).distinct()


@login_required
def home_view(request):
    stories = list(_my_stories(request.user))
    selected = None
    wanted = request.GET.get("story")
    if wanted and wanted.isdigit():
        selected = next((s for s in stories if s.pk == int(wanted)), None)
    selected = selected or (stories[0] if stories else None)
    view = "weave" if request.GET.get("view") == "weave" else "home"
    return render(request, "home/home.html", {
        "view": view,
        "nav_avatar": getattr(Profile.objects.filter(user=request.user).first(), "avatar_url", None),
        "stories": stories,
        "selected": selected,
        "weave_src": reverse("editor:weave", args=[selected.pk]) + "?embed=1" if selected else None,
    })


@login_required
@require_POST
def create_story(request):
    title = (request.POST.get("title") or "").strip()[:150] or "Untitled story"
    story = Story.objects.create(author=request.user, title=title)
    return redirect(f"{reverse('home:home')}?view=weave&story={story.pk}")
