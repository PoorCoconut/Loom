"""The story player: starts sessions, decides which choices are available, and applies them."""

from django.db import transaction

from apps.editor.logic import apply_modifier, check_requirement, coerce
from apps.editor.models import Path

from .models import ReadingSession


class StoryError(Exception):
    """Raised when a reader tries to do something the story doesn't allow."""


def start_session(story, user=None):
    if story.is_deleted or not story.is_published:
        raise StoryError("This story isn't published.")
    if not story.starting_node_id:
        raise StoryError("This story has no starting node.")

    state = {v.variable_name: coerce(v.default_value, v.data_type) for v in story.variables.all()}
    return ReadingSession.objects.create(
        story=story,
        user=user if getattr(user, "is_authenticated", False) else None,
        current_node=story.starting_node,
        variable_state=state,
    )


def _passes(path, state):
    for cond in path.conditions.select_related("variable"):
        if not cond.requirement_type:
            continue
        var = cond.variable
        current = state.get(var.variable_name, coerce(var.default_value, var.data_type))
        if not check_requirement(current, cond.requirement_type, cond.value, var.data_type):
            return False
    return True


def get_choices(session):
    """Paths leaving the current node whose requirements the reader currently meets."""
    paths = Path.objects.filter(source_node=session.current_node, target_node__is_deleted=False)
    return [p for p in paths.select_related("target_node") if _passes(p, session.variable_state)]


@transaction.atomic
def choose(session, path_id):
    session = ReadingSession.objects.select_for_update().get(pk=session.pk)
    if session.is_completed:
        raise StoryError("This playthrough is already finished.")

    path = next((p for p in get_choices(session) if p.pk == int(path_id)), None)
    if path is None:
        raise StoryError("That choice isn't available.")

    state = dict(session.variable_state)
    for cond in path.conditions.select_related("variable"):
        if not cond.modifier_type:
            continue
        var = cond.variable
        current = state.get(var.variable_name, coerce(var.default_value, var.data_type))
        state[var.variable_name] = apply_modifier(current, cond.modifier_type, cond.value, var.data_type)

    session.variable_state = state
    session.current_node = path.target_node
    session.is_completed = not Path.objects.filter(
        source_node=path.target_node, target_node__is_deleted=False
    ).exists()
    session.save()
    return session


def restart(session):
    fresh = {v.variable_name: coerce(v.default_value, v.data_type) for v in session.story.variables.all()}
    session.variable_state = fresh
    session.current_node = session.story.starting_node
    session.is_completed = False
    session.save()
    return session
