from django.conf import settings
from django.db import models
from django.db.models import Q
from simple_history.models import HistoricalRecords

from .currency import Currency
from .date import DateField
from .entity import Entity
from .source import DataLoadSource
from .transfer import Transfer
from .utils import TimestampedModel

# What a declaration does to the organization's supports, once published
DECLARATION_KIND_NEW = "new"
DECLARATION_KIND_CONFIRMATION = "confirmation"
DECLARATION_KIND_EDIT = "edit"
DECLARATION_KIND_REMOVAL = "removal"
# Reconciliation of possible duplicates: the same support, or not
DECLARATION_KIND_MERGE = "merge"
DECLARATION_KIND_NOT_DUPLICATE = "not_duplicate"
DECLARATION_KIND_CHOICES = {
    DECLARATION_KIND_NEW: "New support",
    DECLARATION_KIND_CONFIRMATION: "Confirmation",
    DECLARATION_KIND_EDIT: "Edit",
    DECLARATION_KIND_REMOVAL: "Removal",
    DECLARATION_KIND_MERGE: "Merge",
    DECLARATION_KIND_NOT_DUPLICATE: "Not a duplicate",
}
# The kinds that declare values, the others only refer to transfers
DECLARATION_KINDS_WITH_VALUES = [DECLARATION_KIND_NEW, DECLARATION_KIND_EDIT]
# The changes of the organization to one support: one pending per transfer
DECLARATION_KINDS_SUPPORT_CHANGES = [
    DECLARATION_KIND_CONFIRMATION,
    DECLARATION_KIND_EDIT,
    DECLARATION_KIND_REMOVAL,
]
# The kinds about a transfer and `other_transfers`
DECLARATION_KINDS_RECONCILIATION = [
    DECLARATION_KIND_MERGE,
    DECLARATION_KIND_NOT_DUPLICATE,
]

DECLARATION_STATUS_DRAFT = "draft"
DECLARATION_STATUS_SUBMITTED = "submitted"
DECLARATION_STATUS_APPROVED = "approved"
DECLARATION_STATUS_CHOICES = {
    DECLARATION_STATUS_DRAFT: "Draft",
    DECLARATION_STATUS_SUBMITTED: "Submitted",
    DECLARATION_STATUS_APPROVED: "Approved",
}
# Declarations not published yet
DECLARATION_STATUSES_PENDING = [
    DECLARATION_STATUS_DRAFT,
    DECLARATION_STATUS_SUBMITTED,
]

SUBMISSION_STATUS_SUBMITTED = "submitted"
# Approved, and being published by a Celery task
SUBMISSION_STATUS_PUBLISHING = "publishing"
SUBMISSION_STATUS_APPROVED = "approved"
SUBMISSION_STATUS_RETURNED = "returned"
SUBMISSION_STATUS_CHOICES = {
    SUBMISSION_STATUS_SUBMITTED: "Submitted",
    SUBMISSION_STATUS_PUBLISHING: "Publishing",
    SUBMISSION_STATUS_APPROVED: "Approved",
    SUBMISSION_STATUS_RETURNED: "Returned to the member",
}
# Waiting for approval, or being published
SUBMISSION_STATUSES_PENDING = [
    SUBMISSION_STATUS_SUBMITTED,
    SUBMISSION_STATUS_PUBLISHING,
]


class Submission(TimestampedModel):
    """
    A batch of declarations of an organization, submitted to the TSOSI team.
    Approving it publishes all its declarations.
    """

    history = HistoricalRecords()
    entity = models.ForeignKey(
        Entity, on_delete=models.CASCADE, related_name="submissions"
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    # When the member agreed to the publication under CC BY-SA 4.0
    consent_at = models.DateTimeField(null=True)
    status = models.CharField(
        max_length=16,
        choices=SUBMISSION_STATUS_CHOICES,
        default=SUBMISSION_STATUS_SUBMITTED,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    approved_at = models.DateTimeField(null=True)
    # The data load created on approval
    data_load_source = models.ForeignKey(
        DataLoadSource, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    # The published values of the transfers its declarations refer to, at
    # submission, by declaration (see `hub_publication.submission_snapshot`).
    # A transfer changed since then makes the approval fail.
    snapshot = models.JSONField(null=True)
    # Why the last approval failed: the declarations conflicting with the
    # published data
    publication_error = models.TextField(null=True)

    def __str__(self) -> str:
        return f"{self.entity.name} · {self.date_created:%Y-%m-%d}"


class DeclarationQuerySet(models.QuerySet):
    def pending(self):
        """The declarations not published yet."""
        return self.filter(status__in=DECLARATION_STATUSES_PENDING)


class Declaration(TimestampedModel):
    """
    A change that an organization makes to its supports in the Hub: a new
    support, the confirmation, edit or removal of a transfer it's part of,
    or whether possible duplicates are the same support (merge) or not. It
    stays a draft until submitted, and is kept after its approval as the
    record of what the organization declared. Not-duplicates, and new
    supports with `other_transfers` or `other_declarations`, keep those pairs
    from being flagged as possible duplicates again.
    Unlike `Transfer`, its values aren't checked by the database, as they're
    not published.
    """

    objects = DeclarationQuerySet.as_manager()
    history = HistoricalRecords(
        m2m_fields=["agents", "other_transfers", "other_declarations"]
    )
    # The declaring organization
    entity = models.ForeignKey(
        Entity, on_delete=models.CASCADE, related_name="declarations"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    kind = models.CharField(max_length=16, choices=DECLARATION_KIND_CHOICES)
    status = models.CharField(
        max_length=16,
        choices=DECLARATION_STATUS_CHOICES,
        default=DECLARATION_STATUS_DRAFT,
    )
    # The public transfer it confirms, edits or removes, or that it merges
    # with `other_transfers`. Set to null if the transfer is deleted, e.g. by
    # an ingest: the declaration then conflicts with the published data.
    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.SET_NULL,
        null=True,
        related_name="declarations",
    )
    # Reconciliation: for a merge, the transfers that are the same support as
    # `transfer`. For a not-duplicate, those that aren't. For a new support,
    # the matching transfers that it isn't.
    other_transfers = models.ManyToManyField(Transfer, related_name="+")
    # For a new support: the organization's other new supports that it isn't,
    # though they may look the same
    other_declarations = models.ManyToManyField(
        "self", symmetrical=False, related_name="+"
    )
    submission = models.ForeignKey(
        Submission,
        on_delete=models.SET_NULL,
        null=True,
        related_name="declarations",
    )
    # The organization's source transfer, set on approval of a new support,
    # confirmation or edit
    published_transfer = models.ForeignKey(
        Transfer, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    # The declared values, for new supports and edits
    recipient = models.ForeignKey(
        Entity, on_delete=models.RESTRICT, null=True, related_name="+"
    )
    agents = models.ManyToManyField(Entity, related_name="+")
    amount = models.FloatField(null=True)
    currency = models.ForeignKey(Currency, on_delete=models.RESTRICT, null=True)
    date_invoice = DateField(null=True)
    date_payment_emitter = DateField(null=True)
    date_payment_recipient = DateField(null=True)
    date_start = DateField(null=True)
    date_end = DateField(null=True)

    class Meta:
        constraints = [
            # One pending change per support and organization
            models.UniqueConstraint(
                fields=["entity", "transfer"],
                condition=Q(status__in=DECLARATION_STATUSES_PENDING)
                & Q(kind__in=DECLARATION_KINDS_SUPPORT_CHANGES),
                name="one_pending_declaration_per_transfer",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} · {self.entity.name}"
