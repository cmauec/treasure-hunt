"""
This module contains the models for the Treasure Hunt application.
It defines the data structures used to represent treasure hunts and clues,
including their attributes and relationships with other models.
"""

import uuid
import os

from django.db import models
from django.contrib.auth.models import User
from django.db.models import JSONField


def clue_image_path(instance, filename):
    """
    This function generates the file path for storing clue images.

    Parameters:
    instance (Clue): The Clue instance for which the image path is being generated.
    filename (str): The original filename of the image being uploaded.

    Returns:
    str: The generated file path for the clue image.
    """
    ext = os.path.splitext(filename)[1]
    generator_id = uuid.uuid4()
    return (
        f"clue_images/{instance.treasure_hunt.id}/"
        f"clue_{instance.id}/{generator_id}{ext}"
    )


def hunt_image_path(instance, filename):
    """
    This function generates the file path for storing hunt images.

    Parameters:
    instance (TreasureHunt): The TreasureHunt instance for which the image path is being generated.
    filename (str): The original filename of the image being uploaded.

    Returns:
    str: The generated file path for the hunt image.
    """
    ext = os.path.splitext(filename)[1]
    generator_id = uuid.uuid4()
    return f"hunt_images/{instance.id}/{generator_id}{ext}"


class TreasureHunt(models.Model):
    """
    This model represents a treasure hunt.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(
        upload_to=hunt_image_path,
        null=True,
        blank=True,
        help_text="Main image of the treasure hunt",
    )
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="End date of the treasure hunt",
    )
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    points_per_clue = models.IntegerField(
        default=10, help_text="Points awarded for completing each clue"
    )
    completion_points = models.IntegerField(
        default=50, help_text="Points awarded for completing the entire hunt"
    )

    class Meta:
        permissions = [
            ("can_create_hunts", "Can create treasure hunts"),
        ]

    def __str__(self):
        return self.title


class Clue(models.Model):
    """
    This model represents a clue in a treasure hunt.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    treasure_hunt = models.ForeignKey(
        TreasureHunt, related_name="clues", on_delete=models.CASCADE
    )
    order = models.IntegerField()
    hint_text = models.TextField()
    unlock_message = models.TextField(
        default="Congratulations! You have unlocked a new clue.",
        help_text="Message displayed when the user unlocks this clue.",
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    reference_image = models.ImageField(
        upload_to=clue_image_path,
        max_length=255,
        null=True,
        blank=True,
        help_text="Image related to the clue.",
    )
    image_embedding = JSONField(
        null=True,
        blank=True,
        help_text="LLM embedding of the reference image",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Clue {self.order} - {self.treasure_hunt.title}"


class UserProgress(models.Model):
    """
    This model tracks the progress of a user in a specific treasure hunt.
    It includes information about the user's current clue, the time they started,
    and whether they have completed the hunt.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    treasure_hunt = models.ForeignKey(TreasureHunt, on_delete=models.CASCADE)
    current_clue = models.ForeignKey(Clue, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    total_points = models.IntegerField(
        default=0, help_text="Total points earned in this hunt"
    )

    class Meta:
        unique_together = ["user", "treasure_hunt"]

    def __str__(self):
        return f"{self.user.username} - {self.treasure_hunt.title}"
