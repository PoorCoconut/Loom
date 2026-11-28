from django.urls import path

from . import views

app_name = "editor"
urlpatterns = [
    path("join/<str:token>/", views.join_view, name="join"),
    path("<int:story_id>/api/share/", views.api_share, name="api_share"),
    path("<int:story_id>/api/share/<int:link_id>/", views.api_share_link, name="api_share_link"),
    path("<int:story_id>/api/collaborators/<int:collab_id>/", views.api_collaborator, name="api_collaborator"),
    path("<int:story_id>/weave/", views.weave_view, name="weave"),
    path("<int:story_id>/insights/", views.insights_view, name="insights"),
    path("<int:story_id>/api/story/", views.api_story, name="api_story"),
    path("<int:story_id>/api/nodes/", views.api_nodes, name="api_nodes"),
    path("<int:story_id>/api/nodes/<int:node_id>/", views.api_node, name="api_node"),
    path("<int:story_id>/api/positions/", views.api_positions, name="api_positions"),
    path("<int:story_id>/api/start/", views.api_start, name="api_start"),
    path("<int:story_id>/api/paths/", views.api_paths, name="api_paths"),
    path("<int:story_id>/api/paths/<int:path_id>/", views.api_path, name="api_path"),
    path("<int:story_id>/api/paths/<int:path_id>/conditions/", views.api_conditions, name="api_conditions"),
    path("<int:story_id>/api/conditions/<int:condition_id>/", views.api_condition, name="api_condition"),
    path("<int:story_id>/api/variables/", views.api_variables, name="api_variables"),
    path("<int:story_id>/api/variables/<int:variable_id>/", views.api_variable, name="api_variable"),
]
