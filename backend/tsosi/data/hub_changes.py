"""
The changes of a Hub submission, described for its page in the admin: the
support, the values published at submission and once approved, and who
declared it.
"""

from tsosi.data.hub_publication import is_source
from tsosi.data.hub_reconciliation import DATE_FIELDS
from tsosi.data.ingestion.transfer_matching import format_date
from tsosi.models import Declaration, Entity, Submission, Transfer
from tsosi.models.declaration import (
    DECLARATION_KIND_CONFIRMATION,
    DECLARATION_KIND_EDIT,
    DECLARATION_KIND_MERGE,
    DECLARATION_KIND_NEW,
    DECLARATION_KIND_NOT_DUPLICATE,
    DECLARATION_KIND_REMOVAL,
    DECLARATION_KINDS_WITH_VALUES,
)


def format_amount(amount: float | None, currency: str | None) -> str:
    if amount is None:
        return "no amount"
    return f"{amount:,.2f}".rstrip("0").rstrip(".") + f" {currency or ''}"


class SupportFormatter:
    """
    Short descriptions of supports, from their values as in the submission
    snapshots (see `transfer_snapshot`), for the submission page.
    """

    def __init__(self):
        self.names = {}

    def name(self, entity_id) -> str:
        if entity_id not in self.names:
            entity = Entity.objects.filter(id=entity_id).first()
            self.names[entity_id] = entity.name if entity else "?"
        return self.names[entity_id]

    def date(self, values: dict) -> str:
        for field in [
            "date_payment_recipient",
            "date_payment_emitter",
            "date_invoice",
        ]:
            if values.get(field):
                return format_date(values[field])
        if values.get("date_start"):
            return values["date_start"]["value"][:4]
        return "no date"

    def support(self, values: dict | None) -> str:
        """The date and beneficiary."""
        if not values:
            return "-"
        return f"{self.date(values)} · {self.name(values['recipient'])}"

    def details(self, values: dict | None) -> str:
        """The amount and intermediaries."""
        if not values:
            return "-"
        text = format_amount(values["amount"], values["currency"])
        if values["agents"]:
            agents = ", ".join(self.name(a) for a in values["agents"])
            text += f" via {agents}"
        return text

    def full(self, values: dict | None) -> str:
        return f"{self.support(values)} · {self.details(values)}"


def declaration_values(declaration: Declaration) -> dict:
    """The declared values, like a snapshot of a transfer."""
    return {
        "recipient": str(declaration.recipient_id),
        "agents": [str(a.id) for a in declaration.agents.all()],
        "amount": declaration.amount,
        "currency": declaration.currency_id,
        **{f: getattr(declaration, f) for f in DATE_FIELDS},
    }


def declared_by(transfer: Transfer | None) -> str:
    if transfer is None:
        return "-"
    return ", ".join(
        f"{dls.entity.name if dls.entity else dls.data_source_id} · "
        f"{dls.date_data_obtained}"
        for dls in transfer.data_load_sources.select_related("entity")
    )


def change_after(
    formatter: SupportFormatter,
    declaration: Declaration,
    organization: Entity,
    others: list[dict],
) -> str:
    """What the declaration publishes once approved."""
    kind = declaration.kind
    if kind in DECLARATION_KINDS_WITH_VALUES:
        after = formatter.details(declaration_values(declaration))
    else:
        after = {
            DECLARATION_KIND_CONFIRMATION: (
                f"Unchanged, {organization.name} added as a source"
            ),
            DECLARATION_KIND_REMOVAL: f"{organization.name} removed as a source",
            DECLARATION_KIND_MERGE: "One support with: "
            + "; ".join(formatter.full(o) for o in others),
            DECLARATION_KIND_NOT_DUPLICATE: "Not the same support as: "
            + "; ".join(formatter.full(o) for o in others),
        }[kind]
    transfer = declaration.transfer
    if (
        kind == DECLARATION_KIND_REMOVAL
        and transfer is not None
        and all(
            is_source(organization, t)
            for t in transfer.merged_transfers.all() or [transfer]
        )
    ):
        after += ": the support is deleted, it has no other source"
    if kind == DECLARATION_KIND_NEW and others:
        after += ". Not the same support as: " + "; ".join(
            formatter.full(o) for o in others
        )
    other_new = declaration.other_declarations.all()
    if other_new:
        after += ". Not the same support as the new " + ", ".join(
            f"#{d.id}" for d in other_new
        )
    if kind == DECLARATION_KIND_EDIT:
        after += ". The organization's values are published"
    return after


def submission_changes(submission: Submission) -> list[tuple[str, ...]]:
    """
    Each declaration of the submission: its kind, the support, the values
    published at submission and once approved, and who declared it.
    """
    formatter = SupportFormatter()
    snapshot = submission.snapshot or {}
    declarations = (
        submission.declarations.select_related("transfer")
        .prefetch_related("agents", "other_transfers", "other_declarations")
        .order_by("kind", "date_created")
    )
    rows = []
    for declaration in declarations:
        values = snapshot.get(str(declaration.id), {})
        before = values.get("transfer")
        others = values.get("other_transfers", [])
        if declaration.kind in DECLARATION_KINDS_WITH_VALUES:
            support = formatter.support(declaration_values(declaration))
        else:
            support = formatter.support(before)
        rows.append(
            (
                declaration.get_kind_display(),
                support,
                formatter.details(before) if before else "-",
                change_after(formatter, declaration, submission.entity, others),
                declared_by(declaration.transfer),
            )
        )
    return rows
