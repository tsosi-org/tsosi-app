"""
The submission of the organization's drafts for approval, and the preview
of their publication.
"""

from collections import Counter, defaultdict

from django.core.mail import send_mail
from django.urls import reverse
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from tsosi.api.hub.base import (
    HubView,
    IsMemberOrStaff,
    get_declaring_entity,
    get_hub_entity,
    hub_entities,
)
from tsosi.api.hub.entities import (
    HubTransferSerializer,
    transfers_entity_ids,
    with_table_values,
)
from tsosi.api.hub.session import run_in_background
from tsosi.app_settings import app_settings
from tsosi.data.hub_publication import (
    DraftsChanged,
    simulate_publication,
    submit_declarations,
)
from tsosi.models import Declaration, Submission, Transfer
from tsosi.models.declaration import (
    DECLARATION_KIND_CHOICES,
    SUBMISSION_STATUSES_PENDING,
)

NEW_SUBMISSION_EMAIL_SUBJECT = "[TSOSI Hub] New submission: {name}"
NEW_SUBMISSION_EMAIL_MESSAGE = """{user} submitted {count} for {name}
in the Data Contribution Hub, waiting for approval:

{changes}

Admin page, to approve or return it: {admin_url}
"""


class SubmitSerializer(serializers.Serializer):
    consent = serializers.BooleanField()
    # The draft declarations previewed, and their hash (`declaration_ids`
    # and `declarations_hash` of the preview)
    declaration_ids = serializers.ListField(child=serializers.IntegerField())
    declarations_hash = serializers.CharField()

    def validate_consent(self, value: bool) -> bool:
        if not value:
            raise ValidationError(
                "Agree to the publication of the data under CC BY-SA 4.0 to "
                "submit it."
            )
        return value


class SubmissionSerializer(serializers.ModelSerializer):
    """A submission of the organization, with its number of changes."""

    submitted_by = serializers.SerializerMethodField()
    changes_count = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = ["id", "status", "consent_at", "submitted_by", "changes_count"]

    def get_submitted_by(self, obj: Submission) -> str | None:
        return obj.submitted_by.email if obj.submitted_by else None

    def get_changes_count(self, obj: Submission) -> int:
        return obj.declarations.count()


class EntitySubmissionsView(HubView):
    """
    GET: the organization's submissions waiting for approval, for its
    members and the TSOSI team.
    POST: submit all the organization's draft declarations for approval, as
    one submission, with the agreement to their publication under CC BY-SA
    4.0 (`consent`). They're read-only until approved or returned. They must
    be those previewed, with the same values (`declaration_ids` and
    `declarations_hash` of the preview), e.g. not added, removed or edited
    by another member since.
    """

    permission_classes = [IsMemberOrStaff]

    def get(self, request, entity_id: str):
        entity = get_hub_entity(request.user, entity_id)
        submissions = (
            Submission.objects.filter(
                entity=entity, status__in=SUBMISSION_STATUSES_PENDING
            )
            .select_related("submitted_by")
            .order_by("date_created")
        )
        return Response(SubmissionSerializer(submissions, many=True).data)

    def post(self, request, entity_id: str):
        entity = get_declaring_entity(request.user, entity_id)
        serializer = SubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            submission = submit_declarations(
                entity,
                request.user,
                serializer.validated_data["declaration_ids"],
                serializer.validated_data["declarations_hash"],
            )
        except DraftsChanged:
            raise ValidationError(
                {
                    "detail": "The changes changed since the preview, e.g. "
                    "by another member: reload the page to see them before "
                    "submitting."
                }
            ) from None
        if submission is None:
            raise ValidationError({"detail": "There are no changes to submit."})
        notify_team(request, submission)
        return Response(SubmissionSerializer(submission).data, status=201)


def notify_team(request, submission: Submission) -> None:
    """
    E-mail the TSOSI team (`TSOSI_TEAM_EMAILS`) about a submission waiting
    for approval. Sent in the background: a failure doesn't prevent the
    submission.
    """
    recipients = app_settings.TEAM_EMAILS
    if not recipients:
        return
    kinds = Counter(submission.declarations.values_list("kind", flat=True))
    changes = "\n".join(
        f"- {DECLARATION_KIND_CHOICES.get(kind, kind)}: {count}"
        for kind, count in kinds.most_common()
    )
    run_in_background(
        send_mail,
        NEW_SUBMISSION_EMAIL_SUBJECT.format(name=submission.entity.name),
        NEW_SUBMISSION_EMAIL_MESSAGE.format(
            user=request.user.email,
            count=(f"{kinds.total()} change{'s' if kinds.total() > 1 else ''}"),
            name=submission.entity.name,
            changes=changes,
            admin_url=request.build_absolute_uri(
                reverse("admin:tsosi_submission_change", args=[submission.pk])
            ),
        ),
        # Sent from DEFAULT_FROM_EMAIL
        None,
        recipients,
    )


class EntityPublicationPreviewView(HubView):
    """
    GET: the organization's public supports once its changes not published
    (drafts) are published, simulated without saving: the transfers as on
    its public page (`transfers`), the changes on each one (`changes`, the
    kinds of declarations by transfer ID), and their entities missing from
    the frontend's reference data (`entities`, see `hub_entities`), and the
    drafts previewed and the hash of their values (`declaration_ids` and
    `declarations_hash`, sent with the submission).
    Hidden amounts are left out (`amount_hidden`), the others are given in
    their own currency only (`unconverted`) when they're new or changed.
    """

    permission_classes = [IsMemberOrStaff]

    def get(self, request, entity_id: str):
        entity = get_hub_entity(request.user, entity_id)

        def read(results: dict, declarations_hash: str) -> dict:
            changes = defaultdict(list)
            declarations = Declaration.objects.filter(id__in=results.keys())
            for declaration in declarations.order_by("date_created"):
                transfer = results[declaration.id]
                if transfer is not None:
                    changes[str(transfer.id)].append(declaration.kind)
            transfers = list(
                with_table_values(
                    Transfer.objects.public()
                    .filter(is_future=False)
                    .filter_by_entity(entity)
                )
            )
            data = HubTransferSerializer(
                transfers, many=True, context={"entity": entity}
            ).data
            for transfer, values in zip(transfers, data, strict=True):
                # Masked as on the public page: the list includes the
                # supports of the organization's children
                if values["amount_hidden"]:
                    values.update(amount=None, currency=None, amounts_clc=None)
                values["unconverted"] = (
                    values["amount"] is not None and not transfer.amounts_clc
                )
                if values["unconverted"]:
                    values["amounts_clc"] = {
                        transfer.currency_id: transfer.amount
                    }
            entity_ids = {entity.id} | transfers_entity_ids(transfers)
            return {
                "transfers": data,
                "changes": changes,
                "entities": hub_entities(request, entity_ids),
                "declaration_ids": sorted(results),
                "declarations_hash": declarations_hash,
            }

        return Response(simulate_publication(entity, read))
