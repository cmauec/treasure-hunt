from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_alter_clue_image_embedding"),  # Última migración en tu proyecto
    ]

    operations = [VectorExtension()]
