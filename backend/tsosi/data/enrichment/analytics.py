import logging

import pandas as pd
from django.db import transaction
from django.db.models import F
from tsosi.data.db_utils import bulk_create_from_df
from tsosi.models import Analytic, Transfer

logger = logging.getLogger(__name__)


@transaction.atomic
def compute_analytics():
    """
    Generate analytics table of pre-computed data.
    """
    logger.info("Computing analytics.")
    transfers = (
        Transfer.objects.prefetch_related("emitter", "recipient", "agent")
        .filter(
            merged_into__isnull=True,
            amounts_clc__isnull=False,
            date_clc__isnull=False,
        )
        .values(
            "amounts_clc",
            "date_clc",
            "recipient_id",
            country=F("emitter__country"),
        )
    )
    df = pd.DataFrame.from_records(transfers)
    if df.empty:
        logger.info("No transfer to compute analytics for.")
        return

    # Flatten data
    date_extract = pd.json_normalize(df["date_clc"]).add_prefix("date_")
    df = pd.concat([df, date_extract], axis=1)
    df["date_value"] = pd.to_datetime(df["date_value"], errors="raise")
    df["year"] = df["date_value"].dt.year
    amounts = pd.json_normalize(df["amounts_clc"])
    df = pd.concat([df, amounts], axis=1)
    df.drop(
        columns=["date_clc", "date_precision", "amounts_clc", "date_value"],
        inplace=True,
    )

    # Compute buckets
    aggregations = {}
    currencies = amounts.columns
    for c in currencies:
        aggregations[c] = pd.NamedAgg(column=c, aggfunc="sum")
    aggregations["count"] = pd.NamedAgg(column=c, aggfunc="count")
    data: pd.DataFrame = df.groupby(
        ["country", "recipient_id", "year"], dropna=False
    ).agg(**aggregations)
    data["data"] = data.to_dict(orient="index").values()
    data = data["data"].reset_index()

    # Write in DB
    Analytic.objects.all().delete()
    fields = ["recipient_id", "country", "year", "data"]
    bulk_create_from_df(Analytic, data, fields)

    logger.info(f"Computed {len(data)} analyics.")
