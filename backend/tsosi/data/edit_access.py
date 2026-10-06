from tsosi.app_settings import app_settings
from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI
from tsosi.models import Entity, EntityEditAccess


def entity_edit_url(entity: Entity | None, key: str) -> str:
    """
    Return the frontend URL granting edit access to the entity
    """
    if entity is None:
        return f"{app_settings.FRONTEND_URL}/#edit={key}"
    tsosi_id = entity.identifiers.filter(registry_id=REGISTRY_TSOSI).first()
    entity_ref = tsosi_id.value if tsosi_id else entity.id
    return f"{app_settings.FRONTEND_URL}/entities/{entity_ref}#edit={key}"


def grant_edit_access(
    entity: Entity | None, email: str | None = None, days: int | None = None
) -> tuple[EntityEditAccess, str]:
    """
    Create a temporary edit access to the entity, for the given optional
    grantee email.
    """
    if days is None:
        days = 1 if entity is None else app_settings.EDIT_ACCESS_DAYS
    access, key = EntityEditAccess.create_with_key(entity, email, days)
    return access, entity_edit_url(entity, key)
