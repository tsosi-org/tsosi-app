from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone

from .entity import Entity
from .utils import TimestampedModel


def hash_access_key(key: str) -> str:
    """Return the hash of an access key, as stored in the database."""
    return hashlib.sha256(key.encode()).hexdigest()


class EntityEditAccessQuerySet(models.QuerySet):
    def valid(self):
        """Filter the accesses that are neither expired nor revoked."""
        return self.filter(
            date_expires__gt=timezone.now(), date_revoked__isnull=True
        )

    def get_by_key(self, key: str) -> EntityEditAccess:
        """
        Return the valid access matching the given raw key.
        Raise `EntityEditAccess.DoesNotExist` if there's none.
        """
        return (
            self.valid()
            .select_related("entity")
            .get(key_hash=hash_access_key(key))
        )


class EntityEditAccess(TimestampedModel):
    """
    A temporary access key granting the right to edit an entity's data.
    The raw key is only given to the grantee, we only store its hash.
    An access without entity is an admin access, granting the right to edit
    all entities.
    """

    objects = EntityEditAccessQuerySet.as_manager()
    id = models.BigAutoField(primary_key=True)
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name="edit_accesses",
        null=True,
    )
    # Optional e-mail of the grantee, used to identify who made the edits
    email = models.EmailField(max_length=256, null=True)
    key_hash = models.CharField(max_length=64, unique=True)
    date_expires = models.DateTimeField()
    date_revoked = models.DateTimeField(null=True)
    date_last_used = models.DateTimeField(null=True)

    @classmethod
    def create_with_key(
        cls, entity: Entity | None, email: str | None, days: int
    ) -> tuple[EntityEditAccess, str]:
        """
        Create a new access for the given entity and email.
        No entity means an admin access to all entities.
        Return the access and the raw key. The raw key is not stored and
        can't be retrieved afterwards.
        """
        key = secrets.token_urlsafe(32)
        access = cls.objects.create(
            entity=entity,
            email=email,
            key_hash=hash_access_key(key),
            date_expires=timezone.now() + timedelta(days=days),
        )
        return access, key

    @property
    def grantee(self) -> str:
        """A label identifying the grantee, for logging purposes."""
        return self.email or f"edit access #{self.id}"

    def grants(self, entity: Entity) -> bool:
        """Whether the access grants the right to edit the entity."""
        return self.entity_id is None or self.entity_id == entity.id

    @property
    def is_valid(self) -> bool:
        return self.date_revoked is None and self.date_expires > timezone.now()


class EntityEditLog(TimestampedModel):
    """
    Logs every entity edit performed through an `EntityEditAccess`.
    """

    id = models.BigAutoField(primary_key=True)
    entity = models.ForeignKey(
        Entity, on_delete=models.CASCADE, related_name="edit_logs"
    )
    access = models.ForeignKey(
        EntityEditAccess, on_delete=models.CASCADE, related_name="edit_logs"
    )
    # Mapping field -> {"old": old_value, "new": new_value}
    changes = models.JSONField()
