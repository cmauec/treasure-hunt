"""
This module contains the admin configurations for the Treasure Hunt application.
It registers the models with the Django admin site and customizes their display
and filtering options for better management of treasure hunts, clues, and user progress.
"""

from django.contrib import admin
from .models import TreasureHunt, Clue, UserProgress


@admin.register(TreasureHunt)
class TreasureHuntAdmin(admin.ModelAdmin):
    """
    Admin configuration for the TreasureHunt model.
    """

    list_display = [
        "title",
        "creator",
        "created_at",
        "end_date",
        "is_active",
        "is_public",
        "points_per_clue",
        "completion_points",
    ]
    list_filter = ["is_active", "is_public", "created_at", "end_date"]
    search_fields = ["title", "description", "creator__username"]


@admin.register(Clue)
class ClueAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Clue model.
    """

    list_display = ["treasure_hunt", "order", "created_at"]
    list_filter = ["treasure_hunt", "created_at"]
    ordering = ["treasure_hunt", "order"]


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    """
    Admin configuration for the UserProgress model.
    """

    list_display = [
        "user",
        "treasure_hunt",
        "started_at",
        "is_completed",
        "total_points",
        "completed_at",
    ]
    list_filter = ["is_completed", "started_at"]
    search_fields = ["user__username", "treasure_hunt__title"]
