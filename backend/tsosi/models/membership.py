from django.conf import settings
from django.db import models
from django.db.models import Q

from .entity import Entity
from .utils import TimestampedModel

MEMBERSHIP_STATUS_ACTIVE = "active"
MEMBERSHIP_STATUS_REVOKED = "revoked"
MEMBERSHIP_STATUS_CHOICES = {
    MEMBERSHIP_STATUS_ACTIVE: "Active",
    MEMBERSHIP_STATUS_REVOKED: "Revoked",
}


class MembershipQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=MEMBERSHIP_STATUS_ACTIVE)


class Membership(TimestampedModel):
    """
    Links a user to the organization whose Hub they can use.
    Memberships are created by the TSOSI team. A user has one active
    membership at most.
    """

    objects = MembershipQuerySet.as_manager()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    entity = models.ForeignKey(
        Entity, on_delete=models.CASCADE, related_name="memberships"
    )
    status = models.CharField(
        max_length=16,
        choices=MEMBERSHIP_STATUS_CHOICES,
        default=MEMBERSHIP_STATUS_ACTIVE,
    )
    can_declare_supports = models.BooleanField(default=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "entity"], name="unique_membership"
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status=MEMBERSHIP_STATUS_ACTIVE),
                name="one_active_membership_per_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} · {self.entity.name}"
