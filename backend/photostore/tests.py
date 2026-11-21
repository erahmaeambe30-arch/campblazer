"""Photo upload tests: admin uploads go into PostgreSQL, not onto the server's disk.

    python manage.py test photostore
"""
import os
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Role
from destinations.models import Destination, DestinationImage

from .models import StoredPhoto

# Smallest valid PNG (1x1 pixel).
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
       b"\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")
TMP_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class PhotoUploadTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.dest = Destination.objects.create(name="Test Beach", category="BEACH", municipality="Almeria",
                                               short_description="Test")
        self.admin = User.objects.create_user("admin_t", password="x-Strong-pass-1")
        self.admin.profile.role = Role.ADMIN
        self.admin.profile.save()
        self.camper = User.objects.create_user("camper_t", password="x-Strong-pass-1")
        self.c = APIClient()

    def upload(self, content=PNG, name="beach.png", **extra):
        f = SimpleUploadedFile(name, content, content_type="image/png")
        data = {"destination": self.dest.id, "credit": "Own photo", "caption": "Shore", "image_file": f, **extra}
        return self.c.post("/api/admin/images/", data, format="multipart")

    def test_admin_upload_is_stored_in_database_and_served(self):
        self.c.force_authenticate(self.admin)
        r = self.upload(is_cover="true")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(r.data["stored_in_database"])
        photo = StoredPhoto.objects.get()
        self.assertEqual(bytes(photo.data), PNG)
        self.assertEqual(photo.content_type, "image/png")
        self.assertEqual(photo.uploaded_by, self.admin)
        self.assertEqual(r.data["src"], f"/api/photos/{photo.id}/")
        self.assertEqual(os.listdir(TMP_MEDIA), [])  # nothing written to the server disk

        # Public endpoint returns the exact bytes, cacheable, and 304 on a repeat request.
        self.c.force_authenticate(None)
        got = self.c.get(r.data["src"])
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.content, PNG)
        self.assertEqual(got["Content-Type"], "image/png")
        again = self.c.get(r.data["src"], HTTP_IF_NONE_MATCH=got["ETag"])
        self.assertEqual(again.status_code, 304)

        # Shows up as the destination's cover in the public catalog.
        detail = self.c.get(f"/api/destinations/{self.dest.slug}/")
        self.assertEqual(detail.data["cover_image"]["url"], r.data["src"])

    def test_only_one_cover_per_destination(self):
        self.c.force_authenticate(self.admin)
        first = self.upload(is_cover="true").data
        second = self.upload(is_cover="true", caption="Second").data
        covers = DestinationImage.objects.filter(destination=self.dest, is_cover=True)
        self.assertEqual(list(covers.values_list("id", flat=True)), [second["id"]])
        self.c.patch(f"/api/admin/images/{first['id']}/", {"is_cover": True}, format="json")
        self.assertEqual(list(covers.values_list("id", flat=True)), [first["id"]])

    def test_delete_removes_bytes(self):
        self.c.force_authenticate(self.admin)
        img = self.upload().data
        self.assertEqual(self.c.delete(f"/api/admin/images/{img['id']}/").status_code, 204)
        self.assertFalse(StoredPhoto.objects.exists())

    def test_non_admin_cannot_upload(self):
        self.c.force_authenticate(self.camper)
        self.assertEqual(self.upload().status_code, 403)
        self.c.force_authenticate(None)
        self.assertIn(self.upload().status_code, (401, 403))
        self.assertFalse(StoredPhoto.objects.exists())

    def test_rejects_non_image_even_if_named_jpg(self):
        self.c.force_authenticate(self.admin)
        r = self.upload(content=b"<script>alert(1)</script>", name="evil.jpg")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(DestinationImage.objects.exists())

    def test_rejects_oversized_photo(self):
        self.c.force_authenticate(self.admin)
        r = self.upload(content=PNG + b"\x00" * (5 * 1024 * 1024))
        self.assertEqual(r.status_code, 400)
        self.assertFalse(StoredPhoto.objects.exists())

    def test_credit_is_required(self):
        self.c.force_authenticate(self.admin)
        r = self.upload(credit="  ")
        self.assertEqual(r.status_code, 400)
