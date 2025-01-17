# Generated by Django 5.1.4 on 2025-01-10 17:48

from django.db import migrations, models
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_alter_clue_reference_image"),
    ]

    operations = [
        migrations.RunSQL(
            """
            ALTER TABLE core_clue 
            DROP COLUMN IF EXISTS image_embedding;
            """,
            reverse_sql="",
        ),
        migrations.AddField(
            model_name="clue",
            name="image_embedding",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.FloatField(),
                size=None,
                null=True,
                blank=True,
                help_text="LLM embedding of the reference image",
            ),
        ),
    ]
