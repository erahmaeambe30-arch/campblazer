"""Attach the team-supplied starter photos to the approved destinations.

The image BYTES are stored in PostgreSQL (photostore.StoredPhoto), the same
way admin uploads are, so they survive restarts on Render.

    python manage.py seed_photos            # add starter photos that are missing (safe to repeat)
    python manage.py seed_photos --reset    # re-import the starter photos from photos.json
                                            # (photos uploaded by admins are NOT touched)
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from destinations.models import Destination, DestinationImage
from photostore.services import sniff_image_type, store_new_photo

PHOTO_DIR = Path(__file__).resolve().parents[3] / "seed_photos"
PENDING = "Permission pending — confirm with owner before public launch"
FP = "https://commons.wikimedia.org/wiki/Special:FilePath/{}?width=1600"
PAGE = "https://commons.wikimedia.org/wiki/File:{}"

COMMONS = [
    dict(destination="Agta Beach Resort", file="Sunset_Agta_Beach_Resort_-_Biliran_Philippines.jpg",
         caption="Sunset at Agta Beach Resort (2007)", credit="Leodb / Wikimedia Commons",
         license="CC BY-SA / GFDL 1.2+"),
]


class Command(BaseCommand):
    help = "Attach photos to the approved destinations."

    def add_arguments(self, p):
        p.add_argument("--reset", action="store_true", help="Delete all destination photos first.")

    def handle(self, *args, reset, **kw):
        manifest = json.loads((PHOTO_DIR / "photos.json").read_text(encoding="utf-8"))["photos"]
        if reset:  # only the starter photos listed here; admin uploads stay
            captions = [p["caption"] for p in manifest] + [p["caption"] for p in COMMONS]
            gone, _ = DestinationImage.objects.filter(caption__in=captions).delete()
            self.stdout.write(f"Removed {gone} starter photo rows.")
        added = 0
        for p in manifest:
            d = Destination.objects.filter(name=p["destination"]).first()
            if not d:
                self.stdout.write(self.style.WARNING(f"Skipped {p['file']}: '{p['destination']}' is not in the catalog."))
                continue
            if d.images.filter(caption=p["caption"]).exists():
                continue
            data = (PHOTO_DIR / p["file"]).read_bytes()
            is_cover = p.get("cover", False) and not d.images.filter(is_cover=True).exists()
            store_new_photo(data=data, content_type=sniff_image_type(data), original_name=p["file"],
                            destination=d, caption=p["caption"], credit=p["credit"], license=PENDING,
                            is_cover=is_cover, order=0 if p.get("cover") else 1)
            added += 1
        for p in COMMONS:
            d = Destination.objects.filter(name=p["destination"]).first()
            if not d:
                continue
            _, created = DestinationImage.objects.get_or_create(
                destination=d, image_url=FP.format(p["file"]),
                defaults=dict(caption=p["caption"], credit=p["credit"], license=p["license"],
                              source_page=PAGE.format(p["file"]), is_cover=False, order=2))
            added += created
        missing = Destination.objects.filter(images__isnull=True).values_list("name", flat=True)
        self.stdout.write(self.style.SUCCESS(f"Added {added} photos (stored in PostgreSQL)."))
        if missing:
            self.stdout.write(self.style.WARNING("Still without a photo: " + ", ".join(missing)))
