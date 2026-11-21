
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from destinations.models import Destination, DestinationImage
from photostore.services import sniff_image_type, replace_photo_bytes


PHOTO_DIR = Path(__file__).resolve().parents[3] / "seed_photos"


class Command(BaseCommand):
    help = "Repair destination photos and store them in PostgreSQL."

    def handle(self, *args, **options):
        manifest_path = PHOTO_DIR / "photos.json"

        if not manifest_path.exists():
            raise CommandError(f"Missing manifest: {manifest_path}")

        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )

        repaired = 0
        skipped = 0

        for item in manifest["photos"]:
            destination = Destination.objects.filter(
                name=item["destination"]
            ).first()

            if not destination:
                self.stdout.write(
                    self.style.WARNING(
                        f"SKIPPED: Destination not found: {item['destination']}"
                    )
                )
                skipped += 1
                continue

            photo_path = PHOTO_DIR / item["file"]

            if not photo_path.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"SKIPPED: File not found: {item['file']}"
                    )
                )
                skipped += 1
                continue

            image = DestinationImage.objects.filter(
                destination=destination
            ).first()

            if not image:
                self.stdout.write(
                    self.style.WARNING(
                        f"SKIPPED: No image record for {item['destination']}"
                    )
                )
                skipped += 1
                continue

            data = photo_path.read_bytes()
            content_type = sniff_image_type(data)

            if not content_type:
                self.stdout.write(
                    self.style.WARNING(
                        f"SKIPPED: Invalid image: {item['file']}"
                    )
                )
                skipped += 1
                continue

            replace_photo_bytes(
                image,
                data=data,
                content_type=content_type,
                original_name=item["file"],
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"REPAIRED: {item['destination']} - {item['file']}"
                )
            )
            repaired += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished. Repaired: {repaired}; Skipped: {skipped}."
            )
        )
