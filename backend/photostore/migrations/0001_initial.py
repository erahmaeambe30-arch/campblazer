import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("destinations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StoredPhoto",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("data", models.BinaryField()),
                ("content_type", models.CharField(max_length=30)),
                ("size_bytes", models.PositiveIntegerField()),
                ("sha256", models.CharField(max_length=64)),
                ("original_name", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("image", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                                               related_name="stored_photo", to="destinations.destinationimage")),
                ("uploaded_by", models.ForeignKey(blank=True, null=True,
                                                  on_delete=django.db.models.deletion.SET_NULL,
                                                  related_name="uploaded_photos", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(condition=models.Q(("size_bytes__gt", 0)), name="stored_photo_not_empty"),
                    models.CheckConstraint(
                        condition=models.Q(("content_type__in", ["image/jpeg", "image/png", "image/webp"])),
                        name="stored_photo_allowed_type"),
                ],
            },
        ),
    ]
