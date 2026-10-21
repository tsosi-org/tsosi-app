from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from tsosi.models import Entity

admin.site.site_header = "TSOSI admin"
admin.site.site_title = "TSOSI admin"


@admin.register(Entity)
class EntityAdmin(SimpleHistoryAdmin):
    """
    Entities come from the data pipeline: only their scope is set here, by
    the curation board. Filter on the scope to list the infrastructures to be
    checked.
    """

    list_display = [
        "name",
        "country",
        "scope",
        "is_recipient",
        "is_emitter",
        "is_agent",
        "is_active",
    ]
    list_editable = ["scope"]
    list_filter = ["scope", "is_recipient", "is_partner", "is_active"]
    search_fields = ["name", "short_name", "identifiers__value"]
    ordering = ["name"]
    fields = [
        "name",
        "short_name",
        "country",
        "website",
        "tsosi_type",
        "pids",
        "scope",
    ]
    readonly_fields = [f for f in fields if f != "scope"]

    @admin.display(description="PIDs")
    def pids(self, entity: Entity) -> str:
        return ", ".join(
            f"{i.registry_id}: {i.value}" for i in entity.identifiers.all()
        )

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
