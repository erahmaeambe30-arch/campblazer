"""Saving and validating photo uploads (used by the admin API and seed_photos)."""
import hashlib
import uuid

from django.db import transaction
from rest_framework.exceptions import ValidationError

from destinations.models import DestinationImage

from .models import StoredPhoto

MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB: keeps the free 0.5 GB Neon database comfortable


def sniff_image_type(data: bytes) -> str:
    """Trust the file's actual bytes, not its name or the browser's Content-Type."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise ValidationError({"image_file": "Not a JPG, PNG or WEBP image."})


def read_upload(f) -> tuple[bytes, str]:
    if f.size > MAX_PHOTO_BYTES:
        raise ValidationError({"image_file": "Photo must be 5 MB or smaller."})
    data = f.read()
    if not data:
        raise ValidationError({"image_file": "The file is empty."})
    return data, sniff_image_type(data)


@transaction.atomic
def store_new_photo(*, data: bytes, content_type: str, original_name: str = "", uploaded_by=None,
                    **image_fields) -> DestinationImage:
    """Create DestinationImage + StoredPhoto in ONE transaction (both rows or neither)."""
    photo_id = uuid.uuid4()
    image = DestinationImage.objects.create(image_url=f"/api/photos/{photo_id}/", **image_fields)
    StoredPhoto.objects.create(id=photo_id, image=image, data=data, content_type=content_type,
                               size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                               original_name=original_name[:200], uploaded_by=uploaded_by)
    if image.is_cover:
        make_cover(image)
    return image


@transaction.atomic
def replace_photo_bytes(image: DestinationImage, *, data: bytes, content_type: str, original_name: str = "",
                        uploaded_by=None) -> DestinationImage:
    StoredPhoto.objects.filter(image=image).delete()
    photo_id = uuid.uuid4()  # new id = new URL, so browsers never show the old cached picture
    StoredPhoto.objects.create(id=photo_id, image=image, data=data, content_type=content_type,
                               size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                               original_name=original_name[:200], uploaded_by=uploaded_by)
    image.image_file = ""
    image.image_url = f"/api/photos/{photo_id}/"
    image.save(update_fields=["image_file", "image_url"])
    return image


def make_cover(image: DestinationImage):
    """Only one cover photo per destination."""
    DestinationImage.objects.filter(destination_id=image.destination_id, is_cover=True).exclude(pk=image.pk) \
        .update(is_cover=False)
