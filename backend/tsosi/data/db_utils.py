from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Type

import pandas as pd
from django.db import models
from django.db.models.fields.json import KT
from django.db.models.functions import Cast

from .utils import chunk_df, clean_null_values, drop_keys

INSERT_CHUNK_SIZE = 100
UPDATE_CHUNK_SIZE = 150

IDENTIFIER_CREATE_FIELDS = [
    "registry_id",
    "value",
    "entity_id",
    "date_created",
    "date_last_updated",
]
IDENTIFIER_MATCHING_CREATE_FIELDS = [
    "entity_id",
    "identifier_id",
    "match_criteria",
    "match_source",
    "date_start",
    "date_created",
    "date_last_updated",
]


@dataclass
class DateExtremas:
    min: date | None = field(default=None)
    max: date | None = field(default=None)


def date_extremas_from_queryset(
    queryset: models.QuerySet,
    fields: Iterable[str],
    groupby: Iterable[str] | None = None,
):
    """
    Return the min. and max. values of the given date fields over
    all instances of the given model.
    The date fields are expected to have the models.date.Date dataclass
    structure.

    :param queryset:    The base queryset used to compute extremas from.
    :type queryset:     QuerySet
    :param fields:      The various fields used to compute the extremas.
    :type fields:       Iterable[str]
    :param groupby:     The grouping fields.
    :type groupby:      Iterable[str] | None
    :returns:           The list of extremas per group. Each item contains the
                        grouping keys along with the `_extremas` field.
                        There's only 1 item if no grouping keys are provided.
    """
    aggregations = {}
    for f in fields:
        field_str = f"temp_str_{f}"
        queryset = queryset.annotate(**{field_str: KT(f"{f}__value")})
        field_date = f"temp_date_{f}"
        function = Cast(field_str, output_field=models.DateField())
        queryset = queryset.annotate(**{field_date: function})
        aggregations[f"min__{f}"] = models.Min(field_date)
        aggregations[f"max__{f}"] = models.Max(field_date)

    if groupby:
        extremas_per_group = list(
            (
                queryset.values(*groupby)
                .annotate(**aggregations)
                .values(*groupby, *aggregations.keys())
            )
        )
    else:
        extremas_per_group = [queryset.aggregate(**aggregations)]

    for group in extremas_per_group:

        mins = [
            v
            for k, v in group.items()
            if k.startswith("min__") and v is not None
        ]
        if len(mins) == 0:
            drop_keys(group, [r"^min__.*", r"^max__.*"])
            group["_extremas"] = DateExtremas(min=None, max=None)
            continue

        v_min = min(mins)
        v_max = max(
            [
                v
                for k, v in group.items()
                if k.startswith("max__") and v is not None
            ]
        )
        drop_keys(group, [r"^min__.*", r"^max__.*"])
        group["_extremas"] = DateExtremas(min=v_min, max=v_max)

    return extremas_per_group


def get_model_class_pk_field(model_class: Type[models.Model]) -> str:
    return model_class._meta.pk.attname


def model_instance_from_row[
    T: models.Model
](model_class: Type[T], row: pd.Series, fields: Iterable[str]) -> T:
    kwargs = {f: row[f] for f in fields}
    return model_class(**kwargs)


def bulk_create_from_df(
    model_class: Type[models.Model],
    data: pd.DataFrame,
    fields: Iterable[str],
    track_id_col: str = "",
):
    """
    Perform bulk insertion of the given model from the given data and fields
    to populate the model.

    :param model_class:     The target model class.
    :param data:            The model data. Each row will correspond to 1 insert
                            statement.
    :param fields:          The the model fields to be populated from the
                            dataframe.
                            WARNING: The dataframe columns must match the
                            model field names.
    :params track_id_col:   The optional dataframe column where to write
                            the inserted instance primary key.

    """
    clean_null_values(data)
    for chunk in chunk_df(data, INSERT_CHUNK_SIZE):
        instances: pd.Series = chunk.apply(
            lambda x: model_instance_from_row(model_class, x, fields), axis=1
        )
        results = model_class.objects.bulk_create(instances.to_list())
        if track_id_col:
            data.loc[chunk.index, track_id_col] = [r.pk for r in results]


def bulk_update_from_df(
    model_class: Type[models.Model],
    data: pd.DataFrame,
    fields: Iterable[str],
):
    """
    Perform bulk udates of the given model from the given data and fields
    to populate the model.

    :param model_class: The target model class.
    :param data:        The model data. Each row will correspond to 1 insert
                        statement.
    :param fields:      The the model fields to be populated from the dataframe.
                        WARNING: The dataframe columns must match the model
                        field names.

    """
    pk_field = get_model_class_pk_field(model_class)
    fields_for_update = [f for f in fields if f != pk_field]

    clean_null_values(data)
    for chunk in chunk_df(data, UPDATE_CHUNK_SIZE):
        instances: pd.Series = chunk.apply(
            lambda x: model_instance_from_row(model_class, x, fields), axis=1
        )
        model_class.objects.bulk_update(
            instances.to_list(), fields=fields_for_update
        )
