"""First-run setup for hosted deployments (called by render-start.sh on every boot).

Seeds the catalog, starter photos and demo accounts ONLY when the database is
empty. After that, the database belongs to the administrators: destinations
they add, toggles they flip and photos they upload are never overwritten or
deleted by a restart.

    python manage.py bootstrap            # seed only if there are no destinations yet
    python manage.py bootstrap --force    # re-run the seeders (restores the 18 approved
                                          # destinations and REMOVES any others)
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from destinations.models import Destination


class Command(BaseCommand):
    help = "Seed demo data on an empty database; do nothing otherwise."

    def add_arguments(self, p):
        p.add_argument("--force", action="store_true")

    def handle(self, *args, force, **kw):
        if Destination.objects.exists() and not force:
            self.stdout.write("Database already has data — skipping seeders (admin changes are kept).")
            return
        call_command("seed_destinations")
        call_command("seed_photos")
        call_command("seed_demo")
