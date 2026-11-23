"""The two database operations behind the Insights screen.

JOIN      -> choices_outline():    Path  JOIN  Node (source)  JOIN  Node (target)
SUBQUERY  -> unreachable_scenes(): Node WHERE node_id NOT IN (SELECT target_node_id FROM paths)
             ending_scenes():      Node WHERE node_id NOT IN (SELECT source_node_id FROM paths)
"""

from django.db.models import Subquery

from .models import Node, Path


def choices_outline(story):
    """JOIN: every live choice together with the scene it starts from and the scene it leads to.

    select_related() makes Django emit INNER JOINs: `paths` is joined to `nodes` twice,
    once through source_node_id and once through target_node_id.
    The is_deleted filters on the joined scenes keep soft-deleted scenes out of the result.
    """
    return (
        Path.objects
        .filter(source_node__story=story, source_node__is_deleted=False, target_node__is_deleted=False)
        .select_related("source_node", "target_node")
        .order_by("source_node__node_title", "path_id")
    )


def unreachable_scenes(story):
    """SUBQUERY: scenes that no choice leads to (other than the opening scene).

    inner query : the ids of every scene that IS the target of some live choice
    outer query : scenes of this story whose id is NOT IN that list
    """
    reachable_ids = (
        Path.objects
        .filter(source_node__story=story, source_node__is_deleted=False)
        .values("target_node_id")
    )
    return (
        Node.objects.filter(story=story)
        .exclude(pk=story.starting_node_id)
        .exclude(pk__in=Subquery(reachable_ids))
        .order_by("node_title")
    )


def ending_scenes(story):
    """SUBQUERY: scenes with no outgoing choice, i.e. the story's endings.

    inner query : the ids of every scene that IS the source of some live choice
    outer query : scenes of this story whose id is NOT IN that list
    """
    has_choices = (
        Path.objects
        .filter(source_node__story=story, target_node__is_deleted=False)
        .values("source_node_id")
    )
    return Node.objects.filter(story=story).exclude(pk__in=Subquery(has_choices)).order_by("node_title")


def generated_sql(queryset):
    """The SQL Django will run (used for the on-screen 'Show the SQL' panels)."""
    return str(queryset.query)
