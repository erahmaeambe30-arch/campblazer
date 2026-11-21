import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from photostore.views import serve_photo

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/photos/<uuid:pk>/", serve_photo, name="photo"),  # image bytes from PostgreSQL
    path("api/auth/", include("accounts.urls")),
    path("api/", include("destinations.urls")),
    path("api/", include("bookings.urls")),
]

# Uploaded destination photos. Served by Django when DEBUG is on, or when SERVE_MEDIA=1
# (laptop hosting through a tunnel with DEBUG off). Large deployments use object storage instead.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif os.getenv("SERVE_MEDIA") == "1":
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]
