"""The Weave screen: a horizontal story graph with an Editor mode and a Reader mode.

One HTML page (`weave`) plus a small JSON API the page talks to. Every write endpoint
checks that the user is the story's author or an `editor` collaborator.
"""

import json
import re
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods

from apps.stories.models import Story, StoryCollaborator

from apps.user_settings.models import UserSettings

from .insights import choices_outline, ending_scenes, generated_sql, unreachable_scenes
from .logic import coerce
from .models import GlobalVariable, Node, Path, PathCondition

VAR_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,99}$")


# ---------------------------------------------------------------- access

def _access(request, story_id):
    """Return (story, can_edit). Raises Http404 if the user may not even read it."""
    story = get_object_or_404(Story, pk=story_id)
    role = "owner" if story.author_id == request.user.id else None
    if role is None:
        link = StoryCollaborator.objects.filter(story=story, user=request.user).first()
        role = link.role if link else None
    can_edit = role in ("owner", "editor")
    if not (can_edit or role == "viewer" or story.is_published):
        raise Http404("Story not found.")
    return story, can_edit


# ---------------------------------------------------------------- serializers

def _node(n):
    return {
        "id": n.node_id, "title": n.node_title, "text": n.text_content,
        "x": n.canvas_x, "y": n.canvas_y, "image": n.image_url or "", "audio": n.audio_url or "",
    }


def _cond(c):
    return {
        "id": c.condition_id, "variable": c.variable_id, "req": c.requirement_type or "",
        "mod": c.modifier_type or "", "value": c.value,
    }


def _path(p, conds=None):
    return {
        "id": p.path_id, "source": p.source_node_id, "target": p.target_node_id, "text": p.choice_text,
        "conditions": [_cond(c) for c in (conds if conds is not None else p.conditions.all())],
    }


def _variable(v):
    return {"id": v.variable_id, "name": v.variable_name, "type": v.data_type, "default": v.default_value}


def _graph(story):
    nodes = list(Node.objects.filter(story=story).order_by("node_id"))
    alive = {n.node_id for n in nodes}
    paths = (
        Path.objects.filter(source_node_id__in=alive, target_node_id__in=alive)
        .prefetch_related("conditions").order_by("path_id")
    )
    return {
        "story": {
            "id": story.story_id, "title": story.title, "synopsis": story.synopsis or "",
            "start": story.starting_node_id if story.starting_node_id in alive else None,
            "published": story.is_published,
        },
        "nodes": [_node(n) for n in nodes],
        "paths": [_path(p) for p in paths],
        "variables": [_variable(v) for v in story.variables.all().order_by("variable_id")],
    }


# ---------------------------------------------------------------- page

@login_required
@xframe_options_sameorigin
def weave_view(request, story_id):
    story, can_edit = _access(request, story_id)
    focus = request.GET.get("node")
    focus = int(focus) if focus and focus.isdigit() and story.nodes.filter(pk=focus).exists() else None
    prefs, _ = UserSettings.objects.get_or_create(user=request.user)
    api_base = reverse("editor:api_nodes", args=[story.pk]).rsplit("/nodes/", 1)[0]
    return render(request, "editor/weave.html", {
        "story": story,
        "embed": request.GET.get("embed") == "1",
        "weave": {**_graph(story), "canEdit": can_edit, "apiBase": api_base,
                  "me": request.user.get_username(), "prefs": prefs.weave_prefs(), "focus": focus},
    })


@login_required
@xframe_options_sameorigin
def insights_view(request, story_id):
    story, can_edit = _access(request, story_id)
    if not can_edit:
        raise Http404("Only the author and editors can see Insights.")
    outline_qs = choices_outline(story)
    unreachable_qs = unreachable_scenes(story)
    endings_qs = ending_scenes(story)
    outline = list(outline_qs)
    unreachable, endings = list(unreachable_qs), list(endings_qs)
    embed = request.GET.get("embed") == "1"
    suffix = "?embed=1" if embed else ""
    return render(request, "editor/insights.html", {
        "story": story, "embed": embed, "outline": outline,
        "unreachable": unreachable, "endings": endings,
        "empty_scenes": list(Node.objects.filter(story=story, text_content="")),
        "scene_count": Node.objects.filter(story=story).count(),
        "weave_url": reverse("editor:weave", args=[story.pk]) + suffix,
        "node_url_base": reverse("editor:weave", args=[story.pk]),
        "embed_qs": "&embed=1" if embed else "",
        "sql_join": generated_sql(outline_qs),
        "sql_unreachable": generated_sql(unreachable_qs),
        "sql_endings": generated_sql(endings_qs),
    })


# ---------------------------------------------------------------- api plumbing

def api(methods):
    def deco(fn):
        @wraps(fn)
        @require_http_methods(methods)
        def wrapper(request, story_id, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({"error": "Please log in again."}, status=401)
            try:
                story, can_edit = _access(request, story_id)
                if not can_edit:
                    return JsonResponse({"error": "You can read this story but not edit it."}, status=403)
                body = json.loads(request.body or b"{}")
                with transaction.atomic():
                    data = fn(request, story, body, *args, **kwargs) or {}
                    story.save(update_fields=["last_modified_at"])
                return JsonResponse(data)
            except Http404:
                return JsonResponse({"error": "Not found."}, status=404)
            except ValidationError as exc:
                return JsonResponse({"error": " ".join(exc.messages)}, status=400)
            except (ValueError, TypeError, KeyError) as exc:
                return JsonResponse({"error": str(exc) or "Bad request."}, status=400)
        return wrapper
    return deco


def _int(v, default=0):
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return default


def _node_of(story, pk):
    return get_object_or_404(Node, pk=pk, story=story)


def _drop_paths_touching(node):
    Path.objects.filter(Q(source_node=node) | Q(target_node=node)).delete()  # soft delete


# ---------------------------------------------------------------- nodes

@api(["POST"])
def api_nodes(request, story, body):
    node = Node(
        story=story, node_title=(body.get("title") or "Untitled scene").strip()[:150],
        canvas_x=_int(body.get("x")), canvas_y=_int(body.get("y")),
    )
    node.full_clean()
    node.save()
    out = {"node": _node(node)}
    if not story.starting_node_id:
        story.starting_node = node
        story.save(update_fields=["starting_node"])
        out["start"] = node.node_id
    parent_id = body.get("parent")
    if parent_id:
        parent = _node_of(story, parent_id)
        path = Path(source_node=parent, target_node=node,
                    choice_text=(body.get("choice_text") or "Continue").strip()[:255])
        path.full_clean()
        path.save()
        out["path"] = _path(path, [])
    return out


@api(["PATCH", "DELETE"])
def api_node(request, story, body, node_id):
    node = _node_of(story, node_id)
    if request.method == "DELETE":
        _drop_paths_touching(node)
        node.delete()
        out = {"deleted": node_id}
        if story.starting_node_id == node_id:
            story.starting_node = None
            story.save(update_fields=["starting_node"])
            out["start"] = None
        return out
    if "title" in body:
        node.node_title = str(body["title"]).strip()
    if "text" in body:
        node.text_content = str(body["text"])
    for key, attr in (("image", "image_url"), ("audio", "audio_url")):
        if key in body:
            setattr(node, attr, (str(body[key]).strip() or None))
    if "x" in body:
        node.canvas_x = _int(body["x"])
    if "y" in body:
        node.canvas_y = _int(body["y"])
    node.full_clean()
    node.save()
    return {"node": _node(node)}


@api(["POST"])
def api_positions(request, story, body):
    for item in body.get("positions", []):
        Node.objects.filter(pk=item["id"], story=story).update(
            canvas_x=_int(item.get("x")), canvas_y=_int(item.get("y")))
    return {"ok": True}


@api(["POST"])
def api_start(request, story, body):
    story.starting_node = _node_of(story, body["node"])
    story.save(update_fields=["starting_node"])
    return {"start": story.starting_node_id}


# ---------------------------------------------------------------- paths & conditions

@api(["POST"])
def api_paths(request, story, body):
    path = Path(
        source_node=_node_of(story, body["source"]), target_node=_node_of(story, body["target"]),
        choice_text=(body.get("text") or "Continue").strip()[:255],
    )
    path.full_clean()
    path.save()
    return {"path": _path(path, [])}


@api(["PATCH", "DELETE"])
def api_path(request, story, body, path_id):
    path = get_object_or_404(Path, pk=path_id, source_node__story=story)
    if request.method == "DELETE":
        path.delete()
        return {"deleted": path_id}
    if "text" in body:
        path.choice_text = str(body["text"]).strip()
    if "target" in body:
        path.target_node = _node_of(story, body["target"])
    path.full_clean()
    path.save()
    return {"path": _path(path)}


@api(["POST"])
def api_conditions(request, story, body, path_id):
    path = get_object_or_404(Path, pk=path_id, source_node__story=story)
    variable = get_object_or_404(GlobalVariable, pk=body["variable"], story=story)
    cond = PathCondition(
        path=path, variable=variable, requirement_type=body.get("req") or None,
        modifier_type=body.get("mod") or None, value=str(body.get("value", "")).strip(),
    )
    cond.full_clean()
    cond.save()
    return {"condition": _cond(cond)}


@api(["DELETE"])
def api_condition(request, story, body, condition_id):
    cond = get_object_or_404(PathCondition, pk=condition_id, path__source_node__story=story)
    cond.delete()
    return {"deleted": condition_id}


# ---------------------------------------------------------------- variables

@api(["POST"])
def api_variables(request, story, body):
    name = str(body.get("name", "")).strip()
    if not VAR_NAME_RE.match(name):
        raise ValueError("Use letters, numbers and underscores (not starting with a number).")
    dtype = body.get("type", "int")
    default = coerce(body.get("default", "0" if dtype == "int" else ""), dtype)
    var = GlobalVariable(
        story=story, variable_name=name, data_type=dtype,
        default_value=str(default).lower() if dtype == "bool" else str(default),
    )
    var.full_clean()
    var.save()
    return {"variable": _variable(var)}


@api(["DELETE"])
def api_variable(request, story, body, variable_id):
    var = get_object_or_404(GlobalVariable, pk=variable_id, story=story)
    var.delete()
    return {"deleted": variable_id}
