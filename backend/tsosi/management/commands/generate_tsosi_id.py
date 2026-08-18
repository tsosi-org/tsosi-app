from django.core.management.base import BaseCommand

from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI, generate_tsosi_id
from tsosi.models import Entity, Identifier
from tsosi.models.static_data import fill_static_data


class Command(BaseCommand):
    help = "Generate TSOSI ID for all entities that do not have on yet."

    def handle(self, *args, **options):
        fill_static_data()  # Ensure TSOSI registry is present

        count = 0
        for entity in Entity.objects.all():
            # Create a new identifier for the entity
            _, created = Identifier.objects.get_or_create(
                registry_id=REGISTRY_TSOSI,
                entity=entity,
                defaults={"value": generate_tsosi_id()},
            )
            count += int(created)
        print(f"Generated {count} TSOSI IDs.")
