"""
URLs for the core app.
"""

from django.urls import path
from . import views

urlpatterns = [
    path("", views.treasure_hunt_list, name="treasure_hunt_list"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("hunt/<uuid:hunt_id>/", views.view_hunt, name="view_hunt"),
    path("hunt/<uuid:hunt_id>/details/", views.hunt_details, name="hunt_details"),
    path("hunt/<uuid:hunt_id>/inscribe/", views.inscribe_hunt, name="inscribe_hunt"),
    path(
        "verify-location/<uuid:hunt_id>/", views.verify_location, name="verify_location"
    ),
    path("create/", views.create_hunt, name="create_hunt"),
    path("edit/<uuid:hunt_id>/", views.edit_hunt, name="edit_hunt"),
    path("delete/<uuid:hunt_id>/", views.delete_hunt, name="delete_hunt"),
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path(
        "treasure-hunts/delete/<uuid:hunt_id>/", views.delete_hunt, name="delete_hunt"
    ),
    path(
        "treasure-hunts/<uuid:hunt_id>/participants/",
        views.view_hunt_participants,
        name="hunt_participants",
    ),
]
