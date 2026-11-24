from django.db import migrations, models
from django.utils import timezone


def restore_data_sources(apps, schema_editor):
    """Recreate the data sources of the existing data loads."""
    DataSource = apps.get_model("tsosi", "DataSource")
    DataLoadSource = apps.get_model("tsosi", "DataLoadSource")
    now = timezone.now()
    ids = DataLoadSource.objects.values_list(
        "data_source_id", flat=True
    ).distinct()
    DataSource.objects.bulk_create(
        [DataSource(id=i, date_created=now, date_last_updated=now) for i in ids]
    )


class Migration(migrations.Migration):
    """
    Replace the `DataSource` model by a plain `data_source_id` field on
    `DataLoadSource`, kept on the same column.
    """

    dependencies = [
        ("tsosi", "0040_entity_open_science_policy_url"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="dataloadsource",
            name="unique_full_data_per_source_year",
        ),
        migrations.AlterField(
            model_name="dataloadsource",
            name="data_source",
            field=models.CharField(max_length=64, db_column="data_source_id"),
        ),
        migrations.RenameField(
            model_name="dataloadsource",
            old_name="data_source",
            new_name="data_source_id",
        ),
        migrations.AlterField(
            model_name="dataloadsource",
            name="data_source_id",
            field=models.CharField(max_length=64, db_index=True),
        ),
        migrations.AddConstraint(
            model_name="dataloadsource",
            constraint=models.UniqueConstraint(
                condition=models.Q(("full_data", True)),
                fields=("data_source_id", "year"),
                name="unique_full_data_per_source_year",
                nulls_distinct=True,
            ),
        ),
        # Before deleting the model: run after its recreation when reversed.
        migrations.RunPython(migrations.RunPython.noop, restore_data_sources),
        migrations.DeleteModel(
            name="DataSource",
        ),
    ]
