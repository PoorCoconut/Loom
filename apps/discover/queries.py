"""Shared story queries for Home (my library), Discover and Collections.

Search + tag filtering live here so all three screens behave the same way.
"""

from urllib.parse import urlencode

from django.db.models import Count, F, Q

from apps.engagement.models import StoryFavourite, StoryLike
from apps.stories.models import Story, Tag


def visible_stories(user):
    """Stories this user is allowed to open: published ones, their own, and ones shared with them."""
    return Story.objects.filter(Q(is_published=True) | Q(author=user) | Q(collaborators=user)).distinct()


def my_stories(user):
    return Story.objects.filter(Q(author=user) | Q(collaborators=user)).distinct()


def apply_search(qs, q="", tags=()):
    """Every search word must match the title, synopsis, author name or a tag name.
    Every selected tag must be on the story."""
    for word in (q or "").split():
        qs = qs.filter(
            Q(title__icontains=word) | Q(synopsis__icontains=word)
            | Q(author__username__icontains=word) | Q(tags__name__icontains=word)
        )
    for name in tags:
        qs = qs.filter(tags__name=name)
    return qs.distinct()


def card_queryset(qs):
    """Adds what a story card shows: author, tags, star count and scene count."""
    return (
        qs.select_related("author").prefetch_related("tags")
        .annotate(
            star_count=Count("likes", distinct=True),
            scene_count=Count("nodes", filter=Q(nodes__is_deleted=False), distinct=True),
        )
    )


def order_by(qs, sort):
    if sort == "starred":
        return qs.order_by("-star_count", F("published_at").desc(nulls_last=True), "-pk")
    if sort == "title":
        return qs.order_by("title")
    return qs.order_by(F("published_at").desc(nulls_last=True), "-last_modified_at", "-pk")


def marks(user, stories):
    """Which of these stories the user has starred / saved (for the card buttons)."""
    ids = [s.pk for s in stories]
    return (
        set(StoryLike.objects.filter(user=user, story_id__in=ids).values_list("story_id", flat=True)),
        set(StoryFavourite.objects.filter(user=user, story_id__in=ids).values_list("story_id", flat=True)),
    )


def tag_chips(base_qs, active, params, limit=24):
    """Popular tags in `base_qs`, each with a link that toggles it on/off in the current search."""
    ids = base_qs.values("pk")
    tags = (
        Tag.objects.filter(stories__in=ids)
        .annotate(n=Count("stories", filter=Q(stories__in=ids), distinct=True))
        .order_by("-n", "name")[:limit]
    )
    names = {t.name for t in tags} | set(active)
    chips = []
    for name in sorted(names, key=lambda x: (-next((t.n for t in tags if t.name == x), 0), x)):
        on = name in active
        nxt = [t for t in active if t != name] if on else [*active, name]
        query = {k: v for k, v in params.items() if v}
        if nxt:
            query["tag"] = nxt
        chips.append({
            "name": name, "active": on, "url": "?" + urlencode(query, doseq=True),
            "count": next((t.n for t in tags if t.name == name), 0),
        })
    return chips
