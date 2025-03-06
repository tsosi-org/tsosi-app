# Generated by Django 5.1.6 on 2025-03-06 11:05

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import tsosi.models.date
import tsosi.models.entity
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Currency",
            fields=[
                (
                    "date_created",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("date_last_updated", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.CharField(
                        max_length=3,
                        primary_key=True,
                        serialize=False,
                        validators=[
                            django.core.validators.MinLengthValidator(3),
                            django.core.validators.MaxLengthValidator(3),
                        ],
                    ),
                ),
                ("name", models.CharField(max_length=64)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="DataSource",
            fields=[
                (
                    "date_created",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("date_last_updated", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.CharField(max_length=64, primary_key=True, serialize=False),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="EntityType",
            fields=[
                (
                    "date_created",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("date_last_updated", models.DateTimeField(auto_now=True)),
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=128)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Registry",
            fields=[
                (
                    "date_created",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("date_last_updated", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.CharField(max_length=32, primary_key=True, serialize=False),
                ),
                ("name", models.CharField(max_length=128)),
                ("website", models.URLField(max_length=256)),
                ("link_template", models.CharField(max_length=256)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="CurrencyRate",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("value", models.FloatField()),
                ("date", tsosi.models.date.DateField()),
                (
                    "currency",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="tsosi.currency"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="DataLoadSource",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "date_created",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("date_last_updated", models.DateTimeField(auto_now=True)),
                ("data_load_name", models.CharField(max_length=128)),
                ("year", models.IntegerField(null=True)),
                ("full_data", models.BooleanField(default=False)),
                ("date_data_obtained", models.DateField()),
                (
                    "data_source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="tsosi.datasource",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Entity",
            fields=[
                (
                    "date_created",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("date_last_updated", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                ("raw_name", models.CharField(max_length=512)),
                (
                    "raw_country",
                    models.CharField(
                        max_length=2,
                        null=True,
                        validators=[
                            django.core.validators.MinLengthValidator(2),
                            django.core.validators.MaxLengthValidator(2),
                        ],
                    ),
                ),
                ("raw_website", models.URLField(max_length=256, null=True)),
                ("description", models.TextField(null=True)),
                ("manual_logo", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("is_matchable", models.BooleanField(default=True)),
                ("merged_criteria", models.CharField(max_length=512, null=True)),
                ("name", models.CharField(max_length=512)),
                (
                    "country",
                    models.CharField(
                        max_length=2,
                        null=True,
                        validators=[
                            django.core.validators.MinLengthValidator(2),
                            django.core.validators.MaxLengthValidator(2),
                        ],
                    ),
                ),
                ("website", models.URLField(max_length=256, null=True)),
                ("date_inception", models.DateTimeField(null=True)),
                ("logo_url", models.CharField(max_length=256, null=True)),
                (
                    "logo",
                    models.ImageField(
                        max_length=256,
                        null=True,
                        upload_to=tsosi.models.entity.entity_logo_path,
                    ),
                ),
                ("date_logo_fetched", models.DateTimeField(null=True)),
                ("wikipedia_url", models.CharField(max_length=512, null=True)),
                ("wikipedia_extract", models.TextField(null=True)),
                ("date_wikipedia_fetched", models.DateTimeField(null=True)),
                ("coordinates", models.TextField(null=True)),
                ("is_emitter", models.BooleanField(default=False)),
                ("is_recipient", models.BooleanField(default=False)),
                ("is_agent", models.BooleanField(default=False)),
                (
                    "merged_with",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.RESTRICT,
                        to="tsosi.entity",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Analytic",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "country",
                    models.CharField(
                        max_length=2,
                        null=True,
                        validators=[
                            django.core.validators.MinLengthValidator(2),
                            django.core.validators.MaxLengthValidator(2),
                        ],
                    ),
                ),
                ("year", models.IntegerField()),
                ("data", models.JSONField()),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="tsosi.entity"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Identifier",
            fields=[
                (
                    "date_created",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("date_last_updated", models.DateTimeField(auto_now=True)),
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("value", models.CharField(max_length=128)),
                ("is_under_review", models.BooleanField(default=False)),
                (
                    "entity",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="identifiers",
                        to="tsosi.entity",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="IdentifierEntityMatching",
            fields=[
                (
                    "date_created",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("date_last_updated", models.DateTimeField(auto_now=True)),
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "match_criteria",
                    models.CharField(
                        choices=[
                            ("from_input", "The PID was given in the input data."),
                            (
                                "exact_match",
                                "The PID associated name matches exactly to the entity name.",
                            ),
                            (
                                "from_ror",
                                "The PID was fetched from the entity's ROR record.",
                            ),
                            (
                                "from_wikidata",
                                "The PID was fetched from the entity's Wikidata record.",
                            ),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "match_source",
                    models.CharField(
                        choices=[("manual", "manual"), ("automatic", "automatic")],
                        max_length=32,
                    ),
                ),
                ("date_start", models.DateTimeField(default=django.utils.timezone.now)),
                ("date_end", models.DateTimeField(null=True)),
                ("comments", models.TextField()),
                (
                    "entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="tsosi.entity"
                    ),
                ),
                (
                    "identifier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="tsosi.identifier",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="IdentifierVersion",
            fields=[
                (
                    "date_created",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("date_last_updated", models.DateTimeField(auto_now=True)),
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("value", models.JSONField()),
                ("date_start", models.DateTimeField(default=django.utils.timezone.now)),
                ("date_end", models.DateTimeField(null=True)),
                (
                    "date_last_fetched",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                (
                    "identifier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="tsosi.identifier",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="identifier",
            name="current_version",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="tsosi.identifierversion",
            ),
        ),
        migrations.CreateModel(
            name="InfrastructureDetails",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "date_created",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("date_last_updated", models.DateTimeField(auto_now=True)),
                ("infra_finder_url", models.URLField(max_length=256, null=True)),
                ("posi_url", models.URLField(max_length=256, null=True)),
                ("is_scoss_awarded", models.BooleanField(default=False)),
                ("is_partner", models.BooleanField(default=False)),
                ("hide_amount", models.BooleanField(default=False)),
                ("date_data_update", models.DateField(null=True)),
                ("date_data_start", models.DateField(null=True)),
                ("date_data_end", models.DateField(null=True)),
                (
                    "entity",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="infrastructure_details",
                        to="tsosi.entity",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="identifier",
            name="registry",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="tsosi.registry"
            ),
        ),
        migrations.CreateModel(
            name="Transfert",
            fields=[
                (
                    "date_created",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("date_last_updated", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                ("raw_data", models.JSONField()),
                ("amount", models.FloatField(null=True)),
                ("date_clc", tsosi.models.date.DateField(null=True)),
                ("date_invoice", tsosi.models.date.DateField(null=True)),
                ("date_payment", tsosi.models.date.DateField(null=True)),
                ("date_start", tsosi.models.date.DateField(null=True)),
                ("date_end", tsosi.models.date.DateField(null=True)),
                ("description", models.TextField()),
                ("original_id", models.CharField(max_length=256)),
                ("amounts_clc", models.JSONField(null=True)),
                ("hide_amount", models.BooleanField(default=False)),
                ("original_amount_field", models.CharField(max_length=128)),
                (
                    "agent",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.RESTRICT,
                        related_name="transfert_as_agents",
                        related_query_name="transfert_as_agent",
                        to="tsosi.entity",
                    ),
                ),
                (
                    "currency",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.RESTRICT,
                        to="tsosi.currency",
                    ),
                ),
                (
                    "data_load_source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.RESTRICT,
                        to="tsosi.dataloadsource",
                    ),
                ),
                (
                    "emitter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.RESTRICT,
                        related_name="transfert_as_emitters",
                        related_query_name="transfert_as_emitter",
                        to="tsosi.entity",
                    ),
                ),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.RESTRICT,
                        related_name="transfert_as_recipients",
                        related_query_name="transfert_as_recipient",
                        to="tsosi.entity",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TransfertEntityMatching",
            fields=[
                (
                    "date_created",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("date_last_updated", models.DateTimeField(auto_now=True)),
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "transfert_entity_type",
                    models.CharField(
                        choices=[
                            ("emitter", "Emitter"),
                            ("recipient", "Recipient"),
                            ("agent", "Intermediary (group/consortium)"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "match_criteria",
                    models.CharField(
                        choices=[
                            ("auto_match", "The entity was automatically matched."),
                            (
                                "new_entity",
                                "The entity was created for this transfert.",
                            ),
                            (
                                "same_pid",
                                "The entity has the same PID as the referenced one.",
                            ),
                            (
                                "merged",
                                "The previous entity the transfert was referring to was merged to this one.",
                            ),
                            (
                                "is_child",
                                "The entity is a child of the referenced one.",
                            ),
                            (
                                "same_name_only",
                                "The entity has the same name as the referenced one.",
                            ),
                            (
                                "same_name_country",
                                "The entity has the same name and country as the referenced one",
                            ),
                            (
                                "same_name_url",
                                "The entity has the same name and url as the referenced one.",
                            ),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "match_source",
                    models.CharField(
                        choices=[("manual", "manual"), ("automatic", "automatic")],
                        max_length=32,
                    ),
                ),
                ("comments", models.TextField(null=True)),
                (
                    "entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.RESTRICT, to="tsosi.entity"
                    ),
                ),
                (
                    "transfert",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="tsosi.transfert",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="dataloadsource",
            constraint=models.UniqueConstraint(
                condition=models.Q(("full_data", True)),
                fields=("data_source", "year"),
                name="unique_full_data_per_source_year",
                nulls_distinct=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="entity",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("merged_with_id__isnull", True),
                        ("merged_criteria__isnull", True),
                    ),
                    models.Q(
                        ("merged_with_id__isnull", False),
                        ("merged_criteria__isnull", False),
                    ),
                    _connector="OR",
                ),
                name="entity_merged_with_merged_criteria_consistency",
            ),
        ),
        migrations.AddConstraint(
            model_name="entity",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("merged_with_id__isnull", True),
                    models.Q(("merged_with_id", models.F("id")), _negated=True),
                    _connector="OR",
                ),
                name="entity_not_merged_with_self",
            ),
        ),
        migrations.AddConstraint(
            model_name="identifierentitymatching",
            constraint=models.UniqueConstraint(
                condition=models.Q(("date_end__isnull", True)),
                fields=("identifier",),
                name="unique_identifier_with_no_date_end",
            ),
        ),
        migrations.AddConstraint(
            model_name="identifierentitymatching",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    (
                        "match_criteria__in",
                        ["from_input", "exact_match", "from_ror", "from_wikidata"],
                    )
                ),
                name="identifier_entity_valid_match_criteria_choices",
            ),
        ),
        migrations.AddConstraint(
            model_name="identifierentitymatching",
            constraint=models.CheckConstraint(
                condition=models.Q(("match_source__in", ["manual", "automatic"])),
                name="identifier_entity_valid_match_source_choices",
            ),
        ),
        migrations.AddConstraint(
            model_name="identifier",
            constraint=models.UniqueConstraint(
                fields=("registry", "value"), name="unique_value_per_registry"
            ),
        ),
        migrations.AddConstraint(
            model_name="identifier",
            constraint=models.UniqueConstraint(
                fields=("registry", "entity"),
                name="unique_identifier_per_registry_and_entity",
            ),
        ),
        migrations.AddConstraint(
            model_name="transfert",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("date_invoice__isnull", False),
                    ("date_payment__isnull", False),
                    ("date_start__isnull", False),
                    _connector="OR",
                ),
                name="transfert_at_least_one_date",
            ),
        ),
        migrations.AddConstraint(
            model_name="transfert",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("date_start__isnull", True), ("date_end__isnull", True)),
                    models.Q(
                        ("date_start__isnull", False), ("date_end__isnull", False)
                    ),
                    _connector="OR",
                ),
                name="transfert_date_start_and_date_end_consistency",
            ),
        ),
        migrations.AddConstraint(
            model_name="transfert",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("amount__isnull", False), ("currency_id__isnull", False)),
                    models.Q(("amount__isnull", True), ("currency_id__isnull", True)),
                    _connector="OR",
                ),
                name="transfert_amount_currency_consistency",
            ),
        ),
        migrations.AddConstraint(
            model_name="transfertentitymatching",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("transfert_entity_type__in", ["emitter", "recipient", "agent"])
                ),
                name="valid_transfert_entity_type_choices",
            ),
        ),
        migrations.AddConstraint(
            model_name="transfertentitymatching",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    (
                        "match_criteria__in",
                        [
                            "auto_match",
                            "new_entity",
                            "same_pid",
                            "merged",
                            "is_child",
                            "same_name_only",
                            "same_name_country",
                            "same_name_url",
                        ],
                    )
                ),
                name="transfert_entity_valid_match_criteria_choices",
            ),
        ),
        migrations.AddConstraint(
            model_name="transfertentitymatching",
            constraint=models.CheckConstraint(
                condition=models.Q(("match_source__in", ["manual", "automatic"])),
                name="transfert_entity_valid_match_source_choices",
            ),
        ),
    ]
