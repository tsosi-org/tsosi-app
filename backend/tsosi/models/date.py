import re
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd
from django.db import models

from ..exceptions import ValidationError

DATE_PRECISION_YEAR = "year"
DATE_PRECISION_MONTH = "month"
DATE_PRECISION_DAY = "day"
DATE_PRECISION_CHOICES = {
    DATE_PRECISION_YEAR: "Year",
    DATE_PRECISION_MONTH: "Month",
    DATE_PRECISION_DAY: "Day",
}
DATE_FORMAT = "%Y-%m-%d"


@dataclass
class Date:
    value: str
    precision: str
    force_string: bool = field(default=False)

    def __post_init__(self):
        self.validate()

    def validate(self):
        if not self.force_string and (isinstance(self.value, (date, datetime))):
            self.value = self.value.strftime(DATE_FORMAT)
        elif not re.match(r"\d{4}-\d{2}-\d{2}", self.value):
            raise ValidationError(
                f"Provided str date doesn't match format {DATE_FORMAT}"
            )
        if self.precision not in DATE_PRECISION_CHOICES.keys():
            raise ValidationError(
                f"Provided date precision {self.precision} not in available choices {DATE_PRECISION_CHOICES.keys()}"
            )

    def serialize(self):
        return {"value": self.value, "precision": self.precision}


class DateField(models.JSONField):
    """
    Custom field that automatically validate JSON input format.
    """

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        date_obj = Date(**value, force_string=True)


def format_date(value: datetime, date_precision: str) -> dict[str, str] | None:
    """
    Return the JSON date representation from the date value and the precision.
    """
    if pd.isnull(value):
        return None
    return Date(value=value, precision=date_precision).serialize()
