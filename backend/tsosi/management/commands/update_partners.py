from django.core.management.base import BaseCommand
from tsosi.models.static_data import update_partners


class Command(BaseCommand):
    help = "Update partners data (infrastructure related data)."

    def handle(self, *args, **options):
        update_partners()
