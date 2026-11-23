from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.engagement.models import StoryFavourite, StoryLike
from apps.stories.models import Story

from .queries import apply_search, card_queryset, marks, order_by, tag_chips, visible_stories

SORTS = [("new", "Newest"), ("starred", "Most starred"), ("title", "A–Z")]


def _search_params(request):
    q = request.GET.get("q", "").strip()[:100]
    tags = [t.strip().lower() for t in request.GET.getlist("tag") if t.strip()][:5]
    sort = request.GET.get("sort") if request.GET.get("sort") in dict(SORTS) else "new"
    return q, tags, sort


@login_required
def discover_view(request):
    q, tags, sort = _search_params(request)
    base = Story.objects.filter(is_published=True)
    stories = list(order_by(card_queryset(apply_search(base, q, tags)), sort))
    starred, saved = marks(request.user, stories)
    return render(request, "discover/discover.html", {
        "view": "discover", "q": q, "sort": sort, "sorts": SORTS, "active_tags": tags,
        "chips": tag_chips(base, tags, {"q": q, "sort": sort if sort != "new" else ""}),
        "stories": stories, "starred_ids": starred, "saved_ids": saved,
    })


@login_required
def collections_view(request):
    q, tags, sort = _search_params(request)
    tab = "starred" if request.GET.get("tab") == "starred" else "saved"
    rel = {"saved": "favourites", "starred": "likes"}
    mine = visible_stories(request.user)
    counts = {
        "saved": StoryFavourite.objects.filter(user=request.user, story__in=mine.values("pk")).count(),
        "starred": StoryLike.objects.filter(user=request.user, story__in=mine.values("pk")).count(),
    }
    base = mine.filter(**{f"{rel[tab]}__user": request.user})
    stories = list(order_by(card_queryset(apply_search(base, q, tags)), sort))
    starred, saved = marks(request.user, stories)
    return render(request, "discover/collections.html", {
        "view": "collections", "tab": tab, "remove_on": "save" if tab == "saved" else "star", "counts": counts, "q": q, "sort": sort, "sorts": SORTS,
        "chips": tag_chips(base, tags, {"q": q, "tab": tab, "sort": sort if sort != "new" else ""}),
        "stories": stories, "starred_ids": starred, "saved_ids": saved,
    })


@login_required
@require_POST
def toggle_view(request, kind, story_id):
    """Star / unstar (StoryLike) or save / unsave (StoryFavourite) a story."""
    model = {"star": StoryLike, "save": StoryFavourite}.get(kind)
    if not model:
        raise Http404
    story = visible_stories(request.user).filter(pk=story_id).first()
    if not story:
        raise Http404
    row, created = model.objects.get_or_create(user=request.user, story=story)
    if not created:
        row.delete()
    return JsonResponse({"on": created, "stars": StoryLike.objects.filter(story=story).count()})
