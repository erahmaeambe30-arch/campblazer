"""Destination photos stored INSIDE PostgreSQL.

Why: free web hosts (Render) give the server a temporary disk that is wiped on
every restart/deploy, so files saved to MEDIA_ROOT disappear. Keeping the image
bytes in the database makes PostgreSQL the single source of truth for photos,
exactly like it already is for destinations, availability and reservations.

Each uploaded photo = one DestinationImage row (credit, caption, cover flag…)
+ one StoredPhoto row holding the bytes. The DestinationImage.image_url points
to the serving endpoint /api/photos/<uuid>/ so the rest of the system (public
API, frontend) treats it like any other photo link.
"""
import uuid

from django.conf import settings
from django.db import models


class StoredPhoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.OneToOneField("destinations.DestinationImage", on_delete=models.CASCADE,
                                 related_name="stored_photo")
    data = models.BinaryField()                       # PostgreSQL bytea
    content_type = models.CharField(max_length=30)    # image/jpeg | image/png | image/webp
    size_bytes = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)          # used as the HTTP ETag
    original_name = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="uploaded_photos")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(size_bytes__gt=0), name="stored_photo_not_empty"),
            models.CheckConstraint(condition=models.Q(content_type__in=["image/jpeg", "image/png", "image/webp"]),
                                   name="stored_photo_allowed_type"),
        ]

    def __str__(self):
        return f"{self.original_name or self.id} ({self.size_bytes // 1024} KB)"

    @property
    def url(self):
        return f"/api/photos/{self.id}/"
