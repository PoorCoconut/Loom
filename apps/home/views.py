from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.core.guests import is_guest
from apps.discover.queries import apply_search, card_queryset, marks, my_stories, order_by, tag_chips
from apps.discover.views import SORTS, _search_params
from apps.stories.models import Story


@login_required
def home_view(request):
    if is_guest(request.user) and request.GET.get("view") != "weave":
        return redirect("discover:discover")
    mine = my_stories(request.user)
    view = "weave" if request.GET.get("view") == "weave" else "home"
    ctx = {"view": view}

    if view == "weave":
        stories = list(mine)
        selected = None
        wanted = request.GET.get("story")
        if wanted and wanted.isdigit():
            selected = next((s for s in stories if s.pk == int(wanted)), None)
            # Other people's published stories can be read here too (opened from Discover).
            selected = selected or Story.objects.filter(pk=int(wanted), is_published=True).first()
        selected = selected or (stories[0] if stories else None)
        src = reverse("editor:weave", args=[selected.pk]) + "?embed=1" if selected else None
        if src and request.GET.get("mode") == "read":
            src += "&mode=read"
        ctx.update(stories=stories, selected=selected, weave_src=src)
    else:
        q, tags, sort = _search_params(request)
        library = list(order_by(card_queryset(apply_search(mine, q, tags)), sort if sort != "new" else "new"))
        starred, saved = marks(request.user, library)
        ctx.update(
            stories=library, starred_ids=starred, saved_ids=saved, q=q, sort=sort, sorts=SORTS,
            has_any=mine.exists(),
            chips=tag_chips(mine, tags, {"q": q, "sort": sort if sort != "new" else ""}),
        )
    return render(request, "home/home.html", ctx)


@login_required
@require_POST
def create_story(request):
    if is_guest(request.user):
        messages.info(request, "Guests can read but not weave. Create an account to write your own story.")
        return redirect("discover:discover")
    title = (request.POST.get("title") or "").strip()[:150] or "Untitled story"
    story = Story.objects.create(author=request.user, title=title)
    return redirect(f"{reverse('home:home')}?view=weave&story={story.pk}")
