from collections import Counter

from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from simple_history.admin import SimpleHistoryAdmin

from tsosi.api.hub.session import send_invitation
from tsosi.app_settings import app_settings
from tsosi.data.hub_changes import submission_changes
from tsosi.data.hub_publication import (
    SubmissionNotPending,
    approve_submission,
    return_submission,
)
from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI
from tsosi.models import Entity, InfrastructureDetails, Membership, Submission
from tsosi.models.membership import MEMBERSHIP_STATUS_ACTIVE

admin.site.site_header = "TSOSI admin"
admin.site.site_title = "TSOSI admin"


def entity_ref(entity: Entity) -> str:
    """The ID of the entity's URLs on the site: its TSOSI ID, if any."""
    tsosi_id = entity.identifiers.filter(registry_id=REGISTRY_TSOSI).first()
    return tsosi_id.value if tsosi_id else str(entity.id)


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
        "open_science_policy_url",
        "tsosi_type",
        "pids",
        "public_page",
        "hub",
        "hub_submissions",
        "infrastructure_history",
        "scope",
    ]
    readonly_fields = [f for f in fields if f != "scope"]

    @admin.display(description="PIDs")
    def pids(self, entity: Entity) -> str:
        return ", ".join(
            f"{i.registry_id}: {i.value}" for i in entity.identifiers.all()
        )

    @admin.display(description="Public page")
    def public_page(self, entity: Entity):
        """
        Link to the entity's page, in edit mode: the profile is edited there,
        public or in preview.
        """
        url = f"{app_settings.FRONTEND_URL}/entities/{entity_ref(entity)}?edit"
        return format_html(
            '<a href="{}" target="_blank">View / edit public page</a>', url
        )

    @admin.display(description="Hub")
    def hub(self, entity: Entity):
        """
        Link to the organization's Hub, read-only for the TSOSI team.
        """
        url = f"{app_settings.FRONTEND_URL}/hub/{entity_ref(entity)}"
        return format_html(
            '<a href="{}" target="_blank">Open (read-only)</a>', url
        )

    @admin.display(description="Hub submissions")
    def hub_submissions(self, entity: Entity):
        """
        Links to the organization's submissions, and to those using it as
        a beneficiary or intermediary, e.g. an infrastructure to be checked
        that they added.
        """
        url = reverse("admin:tsosi_submission_changelist")
        own = Submission.objects.filter(entity=entity).count()
        using = (
            Submission.objects.filter(
                Q(declarations__recipient=entity)
                | Q(declarations__agents=entity)
            )
            .exclude(entity=entity)
            .select_related("entity")
            .distinct()
        )
        links = [
            format_html(
                '<a href="{}?entity__id__exact={}">Its submissions ({})</a>',
                url,
                entity.id,
                own,
            )
        ]
        for submission in using:
            links.append(
                format_html(
                    'Used in <a href="{}">{}</a>',
                    reverse(
                        "admin:tsosi_submission_change", args=[submission.pk]
                    ),
                    submission,
                )
            )
        return format_html_join(mark_safe("<br>"), "{}", ((l,) for l in links))

    @admin.display(description="Infrastructure details")
    def infrastructure_history(self, entity: Entity):
        """
        Link to the history of the infrastructure details (support page,
        POSI, SCOSS...). The entity's own history is the History button.
        """
        details = InfrastructureDetails.objects.filter(entity=entity).first()
        if details is None:
            return "-"
        url = reverse(
            "admin:tsosi_infrastructuredetails_history", args=[details.pk]
        )
        return format_html('<a href="{}">History</a>', url)

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(InfrastructureDetails)
class InfrastructureDetailsAdmin(SimpleHistoryAdmin):
    """
    Read-only: the infrastructure details are edited on the organization's
    page. Kept for their history, linked from the entity page.
    """

    list_display = ["entity", "support_url", "posi_url"]
    list_select_related = ["entity"]
    search_fields = ["entity__name"]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


class MembershipForm(forms.ModelForm):
    """
    A member is added by e-mail: the user is created if it doesn't exist.
    They can be sent an invitation e-mail, only when added.
    """

    email = forms.EmailField()
    send_invitation = forms.BooleanField(
        label="Send an invitation e-mail",
        required=False,
        initial=True,
        help_text="Tells the new member how to log in to their "
        "organization's Hub, once saved. Only for an active membership.",
    )

    class Meta:
        model = Membership
        fields = [
            "email",
            "entity",
            "status",
            "can_declare_supports",
            "send_invitation",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["email"].initial = self.instance.user.email
            self.fields["email"].disabled = True
            del self.fields["send_invitation"]

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        if self.instance.pk or not email:
            user = self.instance.user if self.instance.pk else None
        else:
            user = get_user_model().objects.filter(email__iexact=email).first()
        if user is None:
            return cleaned_data
        memberships = Membership.objects.filter(user=user).exclude(
            pk=self.instance.pk
        )
        entity = cleaned_data.get("entity")
        if entity and memberships.filter(entity=entity).exists():
            raise forms.ValidationError(
                "This user already has a membership of this organization: "
                "change its status instead."
            )
        other = memberships.active().select_related("entity").first()
        if cleaned_data.get("status") == MEMBERSHIP_STATUS_ACTIVE and other:
            raise forms.ValidationError(
                "A user can only be an active member of one organization. "
                f"This one is already a member of {other.entity.name}."
            )
        self.user = user
        return cleaned_data

    def save(self, commit=True):
        if not self.instance.pk:
            user = getattr(self, "user", None)
            if user is None:
                email = self.cleaned_data["email"].lower()
                user = get_user_model().objects.create_user(
                    username=email, email=email
                )
            self.instance.user = user
        return super().save(commit)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """
    Members of the organizations, who can log in to their Hub and edit
    their organization's profile. Uncheck "Can declare supports" for
    infrastructures and consortia. Revoke a member by changing their status.
    A new member is sent an invitation e-mail, unless unchecked.
    """

    form = MembershipForm
    list_display = [
        "email",
        "entity",
        "status",
        "can_declare_supports",
        "added_by",
        "date_created",
    ]
    list_filter = ["status", "can_declare_supports"]
    list_select_related = ["user", "entity", "added_by"]
    search_fields = ["user__email", "entity__name"]
    autocomplete_fields = ["entity"]
    ordering = ["-date_created"]

    @admin.display(description="E-mail", ordering="user__email")
    def email(self, membership: Membership) -> str:
        return membership.user.email

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if obj is not None:
            # The invitation is only sent to the new members
            fields = [f for f in fields if f != "send_invitation"]
        return fields

    def save_model(self, request, obj, form, change):
        if not change:
            obj.added_by = request.user
        super().save_model(request, obj, form, change)
        if change or not form.cleaned_data.get("send_invitation"):
            return
        if obj.status != MEMBERSHIP_STATUS_ACTIVE:
            self.message_user(
                request,
                "No invitation e-mail was sent: the membership isn't active.",
                messages.WARNING,
            )
            return
        # Sent once the membership is saved, so that the member can log in
        transaction.on_commit(lambda: send_invitation(obj))
        self.message_user(
            request, f"An invitation e-mail was sent to {obj.user.email}."
        )

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(Submission)
class SubmissionAdmin(SimpleHistoryAdmin):
    """
    The declarations submitted by the organizations in the Hub. Approving a
    submission publishes all of them at once, in a Celery task. Returning it
    unlocks them in the Hub, to be fixed and submitted again: the members are
    told why by e-mail.
    """

    list_display = [
        "entity",
        "submitted_by",
        "date_created",
        "status",
        "changes",
        "approved_by",
        "approved_at",
    ]
    list_filter = ["status"]
    list_select_related = ["entity", "submitted_by", "approved_by"]
    search_fields = ["entity__name", "submitted_by__email"]
    ordering = ["-date_created"]
    fields = [
        "organization",
        "submitted_by",
        "consent_at",
        "status",
        "publication_error",
        "approved_by",
        "approved_at",
        "hub_organizations",
        "changes_table",
    ]
    readonly_fields = fields
    change_form_template = "admin/tsosi/submission/change_form.html"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("declarations")

    @admin.display(description="Changes")
    def changes(self, submission: Submission) -> str:
        counts = Counter(
            d.get_kind_display() for d in submission.declarations.all()
        )
        return " · ".join(f"{n} {kind.lower()}" for kind, n in counts.items())

    @admin.display(description="Organization")
    def organization(self, submission: Submission):
        url = reverse("admin:tsosi_entity_change", args=[submission.entity_id])
        hub = f"{app_settings.FRONTEND_URL}/hub/{entity_ref(submission.entity)}"
        return format_html(
            '<a href="{}">{}</a> · <a href="{}" target="_blank">Hub</a>',
            url,
            submission.entity.name,
            hub,
        )

    @admin.display(description="Organizations added in the Hub")
    def hub_organizations(self, submission: Submission):
        """
        The organizations added in the Hub that the declarations use, with
        their IDs and scope: set the scope of the infrastructures to check.
        """
        declarations = submission.declarations.all()
        roles = {}
        for declaration in declarations.prefetch_related("agents"):
            if declaration.recipient_id:
                roles.setdefault(declaration.recipient_id, set()).add(
                    "beneficiary"
                )
            for agent in declaration.agents.all():
                roles.setdefault(agent.id, set()).add("intermediary")
        entities = (
            Entity.objects.filter(id__in=roles, added_in_hub_by__isnull=False)
            .prefetch_related("identifiers")
            .distinct()
        )
        if not entities:
            return "-"
        rows = []
        for entity in entities:
            ids = ", ".join(
                f"{i.registry_id}: {i.value}"
                for i in entity.identifiers.all()
                if i.registry_id != REGISTRY_TSOSI
            )
            rows.append(
                (
                    reverse("admin:tsosi_entity_change", args=[entity.id]),
                    entity.name,
                    ids or "no ID",
                    ", ".join(sorted(roles[entity.id])),
                    entity.get_scope_display() or "no scope: to be checked",
                )
            )
        return format_html(
            "<table><tr><th>Name</th><th>IDs</th><th>Role</th><th>Scope</th>"
            "</tr>{}</table>",
            format_html_join(
                "",
                '<tr><td><a href="{}">{}</a></td><td>{}</td><td>{}</td>'
                "<td>{}</td></tr>",
                rows,
            ),
        )

    @admin.display(description="Changes")
    def changes_table(self, submission: Submission):
        """
        Each declaration, with the values published at submission and once
        approved, and who declared the support.
        """
        return format_html(
            "<table><tr><th>Change</th><th>Support</th>"
            "<th>Currently published</th><th>After approval</th>"
            "<th>Declared by</th></tr>{}</table>",
            format_html_join(
                "",
                "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td>"
                "</tr>",
                submission_changes(submission),
            ),
        )

    def get_urls(self):
        view = self.admin_site.admin_view
        return [
            path(
                "<int:object_id>/approve/",
                view(self.approve_view),
                name="tsosi_submission_approve",
            ),
            path(
                "<int:object_id>/return/",
                view(self.return_view),
                name="tsosi_submission_return",
            ),
            *super().get_urls(),
        ]

    def can_publish(self, request) -> bool:
        return request.user.has_perm("tsosi.change_submission")

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "can_publish": self.can_publish(request),
        }
        return super().change_view(request, object_id, form_url, extra_context)

    def action_submission(self, request, object_id: int) -> Submission:
        """
        The submission, for the POST of an action. Whether it's still waiting
        for approval is checked by the action, under lock: a double click
        gets the `not_pending` message.
        """
        if not self.can_publish(request):
            raise PermissionDenied
        return get_object_or_404(Submission, pk=object_id)

    def not_pending(self, request, object_id: int):
        """Approved or returned by another request at the same time."""
        messages.warning(
            request,
            "The submission isn't waiting for approval any more: it was "
            "approved or returned meanwhile.",
        )
        return redirect("admin:tsosi_submission_change", object_id)

    def approve_view(self, request, object_id: int):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        submission = self.action_submission(request, object_id)
        try:
            approve_submission(submission, request.user)
        except SubmissionNotPending:
            return self.not_pending(request, object_id)
        messages.info(
            request,
            "The submission is being published. Reload the page in a moment "
            "to see the result.",
        )
        return redirect("admin:tsosi_submission_change", object_id)

    def return_view(self, request, object_id: int):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        submission = self.action_submission(request, object_id)
        try:
            return_submission(submission)
        except SubmissionNotPending:
            return self.not_pending(request, object_id)
        messages.info(
            request,
            "The submission is returned: its changes can be edited in the Hub "
            "again. Tell the members why by e-mail.",
        )
        return redirect("admin:tsosi_submission_change", object_id)

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
