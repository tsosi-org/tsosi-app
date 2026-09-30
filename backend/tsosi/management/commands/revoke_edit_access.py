from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone
from tsosi.models import Entity, EntityEditAccess


class Command(BaseCommand):
    help = (
        "Revoke the valid entity edit accesses matching all the given filters."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--id",
            dest="access_id",
            type=int,
            default=None,
            help="The ID of the access, as printed by `grant_edit_access`.",
        )
        parser.add_argument(
            "--email", default=None, help="The e-mail of the grantee."
        )
        parser.add_argument(
            "--entity",
            dest="entity_id",
            default=None,
            help="Any ID of the entity. Doesn't match admin accesses.",
        )

    def handle(self, *args, **options):
        if not any(
            options[k] is not None for k in ["access_id", "email", "entity_id"]
        ):
            raise CommandError(
                "At least one of --id, --email or --entity is required."
            )
        accesses = EntityEditAccess.objects.valid()
        if options["access_id"] is not None:
            accesses = accesses.filter(id=options["access_id"])
        if options["email"] is not None:
            accesses = accesses.filter(email=options["email"])
        if options["entity_id"] is not None:
            entity = Entity.objects.get_by_any_id(options["entity_id"])
            accesses = accesses.filter(entity=entity)
        count = accesses.update(date_revoked=timezone.now())
        self.stdout.write(f"Revoked {count} edit access(es).")
