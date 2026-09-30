from django.core.management.base import BaseCommand, CommandParser

from tsosi.data.edit_access import grant_edit_access
from tsosi.models import Entity


class Command(BaseCommand):
    help = (
        "Grant a temporary access to edit an entity's data, or all entities' "
        "data, and print the edit link to send to the grantee."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument(
            "--entity",
            dest="entity_id",
            help="Any ID of the entity (UUID, TSOSI, ROR, ...)",
        )
        target.add_argument(
            "--all",
            action="store_true",
            help="Grant an admin access to edit all entities.",
        )
        parser.add_argument(
            "--email",
            default=None,
            help="The e-mail of the grantee, used to identify who made edits.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help=(
                "Validity duration of the access, in days. Defaults to 7 "
                "days for an entity, 1 day for an admin access."
            ),
        )

    def handle(self, *args, **options):
        entity = None
        if options["entity_id"]:
            entity = Entity.objects.get_by_any_id(
                options["entity_id"]
            ).sucessor_or_self()
        access, url = grant_edit_access(
            entity, options["email"], days=options["days"]
        )
        target = f"entity `{entity.name}`" if entity else "all entities"
        grantee = f" to {access.email}" if access.email else ""
        self.stdout.write(
            f"Edit access #{access.id} granted{grantee} for {target} until "
            f"{access.date_expires:%Y-%m-%d %H:%M} UTC."
        )
        self.stdout.write(f"Edit link: {url}")
