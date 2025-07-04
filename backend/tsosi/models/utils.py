from django.core.files.base import File
from django.db import models
from django.utils import timezone

MATCH_SOURCE_MANUAL = "manual"
MATCH_SOURCE_AUTOMATIC = "automatic"
MATCH_SOURCE_CHOICES = {
    MATCH_SOURCE_MANUAL: "manual",
    MATCH_SOURCE_AUTOMATIC: "automatic",
}

UUID4_REGEX = r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"


class TimestampedModel(models.Model):
    date_created = models.DateTimeField(default=timezone.now)
    date_last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


def replace_model_file(
    instance: models.Model,
    attribute: str,
    file_path: str,
    read_mode: str = "rb",
):
    """
    Replace a model's file with the one at the given path.
    """
    file_field: models.FieldFile = getattr(instance, attribute)
    if file_field.name is not None:
        file_field.delete()
    name = file_path.split("/")[-1]
    with open(file_path, read_mode) as f:
        file_field.save(name, File(f))
