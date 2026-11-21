from django.http import HttpResponse, HttpResponseNotModified
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from .models import StoredPhoto


@require_GET
def serve_photo(request, pk):
    """GET /api/photos/<uuid>/ — streams the image bytes out of PostgreSQL.

    The URL contains a random UUID that changes whenever the photo is replaced,
    so browsers/CDNs may cache it forever (immutable)."""
    photo = get_object_or_404(StoredPhoto.objects.only("content_type", "sha256", "size_bytes", "data"), pk=pk)
    etag = f'"{photo.sha256}"'
    if request.headers.get("If-None-Match") == etag:
        return HttpResponseNotModified()
    resp = HttpResponse(bytes(photo.data), content_type=photo.content_type)
    resp["Content-Length"] = str(photo.size_bytes)
    resp["ETag"] = etag
    resp["Cache-Control"] = "public, max-age=31536000, immutable"
    resp["X-Content-Type-Options"] = "nosniff"
    return resp
