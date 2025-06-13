from django.core.management.base import BaseCommand
from tsosi.models.static_data import fill_static_data


class Command(BaseCommand):
    help = "Fill static data (registries, sources and infrastructure related data)."

    def handle(self, *args, **options):
        fill_static_data()
