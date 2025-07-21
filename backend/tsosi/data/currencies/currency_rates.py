"""
Contains methods to fetch the currency rate data and related work.
The data is taken from https://data.bis.org
"""

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError
from urllib.parse import urlencode

import pandas as pd
from django.db import transaction
from requests.exceptions import RequestException
from tsosi.data.db_utils import (
    DateExtremas,
    bulk_create_from_df,
    bulk_update_from_df,
    date_extremas_from_queryset,
)
from tsosi.data.task_result import TaskResult
from tsosi.models import Currency, CurrencyRate, Transfer
from tsosi.models.date import (
    DATE_PRECISION_DAY,
    DATE_PRECISION_MONTH,
    DATE_PRECISION_YEAR,
    Date,
)

logger = logging.getLogger(__name__)

CURRENCY_API_URL = (
    "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_XRU/1.0/D.."
)
# Available currencies through bis data portal API
SUPPORTED_CURRENCIES = frozenset(
    [
        "AED",
        "ALL",
        "ARS",
        "AUD",
        "BAM",
        "BGN",
        "BND",
        "BRL",
        "CAD",
        "CHF",
        "CLP",
        "CNY",
        "COP",
        "CZK",
        "DKK",
        "DZD",
        "EUR",
        "GBP",
        "HKD",
        "HUF",
        "IDR",
        "ILS",
        "INR",
        "ISK",
        "JPY",
        "KRW",
        "KWD",
        "LKR",
        "MAD",
        "MKD",
        "MUR",
        "MXN",
        "MYR",
        "NOK",
        "NZD",
        "OMR",
        "PEN",
        "PHP",
        "PLN",
        "QAR",
        "RON",
        "RSD",
        "RUB",
        "SAR",
        "SEK",
        "SGD",
        "THB",
        "TRY",
        "TTD",
        "TWD",
        "UAH",
        "USD",
        "UYU",
        "XDR",
        "ZAR",
    ]
)

CURRENCY_NAMES_FILE = Path(__file__).resolve().parent / "currency_names.json"


def check_currency(currency: str, error=False) -> bool:
    """
    :param currency:    The currency ISO 4217 code
    :param error:       Whether to raise an exception when the currency
                        is not supported
    :return:            Whether the currency is supported
    """
    check = True
    if currency not in SUPPORTED_CURRENCIES:
        if error:
            raise Exception(f"Currency {currency} is not supported")
        logger.warning(f"Currency {currency} is not supported")
        check = False
    return check


def insert_currencies(currencies: Iterable[str], date_update: datetime):
    """
    Insert the given currencies to the database.

    :param currencies:      An iterable of ISO 4217 codes
    :param date_update:     The datetime used to log the creation of the
                            database records

    """
    for c in currencies:
        check_currency(c, error=True)

    with open(CURRENCY_NAMES_FILE, "r") as f:
        currency_mapping = json.load(f)

    existing_currencies = Currency.objects.all().values_list("id", flat=True)

    to_insert = [c for c in currencies if c not in existing_currencies]
    if len(to_insert) == 0:
        return

    instances = []
    for c in to_insert:
        instances.append(
            Currency(
                id=c,
                name=currency_mapping[c],
                date_created=date_update,
                date_last_updated=date_update,
            )
        )
    Currency.objects.bulk_create(instances)


def fetch_currency_rates(
    currencies: Iterable[str], date_start: date, date_end: date
):
    """
    Fetches the nominal exchange rate wrt. USD for the given currencies and
    period with a daily granularity.
    The obtained `rate` must be used as:
    ``{amount} * USD = {rate} * {amount} XYZ``

    :param currencies:  The currency ISO codes.
    :param start_date:  The start date of the period.
    :param end_date:    The end date of the period.
    :return:            The dataframe result of the API request. The columns
                        of interest are TIME_PERIOD, OBS_VALUE, CURRENCY.
    """
    for c in currencies:
        check_currency(c, error=True)

    url = f"{CURRENCY_API_URL}{"+".join(currencies)}"
    query_params = {
        "startPeriod": date_start.strftime("%Y-%m-%d"),
        "endPeriod": date_end.strftime("%Y-%m-%d"),
        "format": "csv",
    }
    url = f"{url}?{urlencode(query_params)}"
    try:
        data = pd.read_csv(url)
    except (RequestException, HTTPError) as e:
        data = pd.DataFrame()
        logger.error(
            f"Error while fetching currency rates for URL {url}.", exc_info=e
        )
    return data


def process_raw_rates(
    rates: pd.DataFrame, date_start: date, date_end: date
) -> pd.DataFrame:
    """
    Process the resulting data from the currency API:
        - Fill missing timesteps with closest value.
        - Return 1 value per currency per timestep

    :param rates:       The dataframe of currency rates, as a result of the
                        currency API.
    :param date_start:  The start date of the queried interval.
    :param date_end:    The end date of the queried interval.
    :return:            The processed rates DataFrame, with columns
                        `currency`, `date`, `rate`
    """
    date_range = pd.date_range(
        start=date_start,
        end=date_end,
        freq="D",
        inclusive="left",
        name="TIME_PERIOD",
    )
    df_c = rates.dropna(subset="OBS_VALUE")
    df_c.loc[:, "TIME_PERIOD"] = pd.to_datetime(
        df_c["TIME_PERIOD"], format="%Y-%m-%d"
    )
    # Keep only 1 value per currency per timestep
    df_c = (
        df_c.groupby(["CURRENCY", "TIME_PERIOD"])
        .first()
        .reset_index(drop=False)
    )

    # Add missing timesteps and fill value from closest observation
    df_c.set_index(["TIME_PERIOD"], inplace=True)
    df_res = df_c.groupby("CURRENCY").apply(
        lambda group: group.reindex(
            date_range, level="TIME_PERIOD", method="nearest"
        ),
        include_groups=False,
    )
    df_res.reset_index(inplace=True)

    cols_of_interest = {
        "CURRENCY": "currency_id",
        "TIME_PERIOD": "date",
        "OBS_VALUE": "value",
    }
    df_res = df_res[cols_of_interest.keys()].rename(columns=cols_of_interest)
    df_res["date"] = df_res["date"].apply(
        lambda x: Date(value=x, precision=DATE_PRECISION_DAY).serialize()
    )
    return df_res


def update_currency_rate(
    currency: str,
    target_interval: DateExtremas,
    currency_interval: DateExtremas,
):
    """
    Update the rates of a single currency to match the given target interval.

    :param currency:            The currency ISO code.
    :param target_interval:     The target interval to match.
    :param currency_interval:   The current interval of already fetched data.
    """
    if target_interval.min is None or target_interval.max is None:
        logger.error("Null `target_interval` passed, aborting update.")
        return

    # Get the intervals for which the rate data is missing (ie.
    # "target_interval \ currency_interval" in set theory).
    # We assume the rate-time intervals present in DB are continuous.
    intervals: list[DateExtremas] = []
    min_date: date | None = currency_interval.min
    max_date: date | None = (
        currency_interval.max + timedelta(days=1)
        if currency_interval.max is not None
        else None
    )
    if min_date is None:
        intervals.append(target_interval)
    elif min_date > target_interval.min:
        intervals.append(DateExtremas(min=target_interval.min, max=min_date))

    if max_date is None:
        pass
    elif max_date < target_interval.max:
        intervals.append(DateExtremas(min=max_date, max=target_interval.max))

    # Fetch data for each interval
    for interval in intervals:
        # Prevent fetching if the interval is less than 8 days
        # The remote data doesn't update everyday and the API returns 404 when
        # there's no data for the queried interval.
        if ((interval.max - interval.min).days < 8) and interval.max > (
            date.today() - timedelta(days=3)
        ):
            logger.info(
                f"Aborting subsequent currency fetching for `{currency}` "
                f"with too small interval {interval.min} - {interval.max}"
            )
            # Return instead of continuing here, if the condition is true
            # it should be the last interval so it's the same.
            # If not, there's an issue and we should abort.
            break

        logger.info(
            f"Updating currency rates for `{currency}` from "
            f"{interval.min} to {interval.max}"
        )
        current_start = interval.min
        while current_start < interval.max:
            current_end = min(current_start + timedelta(days=365), interval.max)
            raw_rates = fetch_currency_rates(
                [currency], current_start, current_end
            )
            # Enforce having a continuous interval of rates.
            # If one interval query fails, don't query the subsequent ones.
            if raw_rates.empty:
                return
            processed_rates = process_raw_rates(
                raw_rates, current_start, current_end
            )
            bulk_create_from_df(
                CurrencyRate, processed_rates, ["currency_id", "date", "value"]
            )
            current_start = current_end


@transaction.atomic
def compute_average_rates():
    """
    Compute average rates per month and year based on existing data.
    """
    logger.info("Computing average currency rates.")
    columns = [
        "currency_id",
        "date",
        "value",
    ]
    data = pd.DataFrame.from_records(
        CurrencyRate.objects.filter(date__precision=DATE_PRECISION_DAY).values(
            *columns
        )
    )
    if data.empty:
        logger.info("No currency rates to compute average for.")
        return

    date_extract = pd.json_normalize(data["date"]).add_prefix("date_")
    data = pd.concat([data, date_extract], axis=1)
    data["date"] = pd.to_datetime(data["date_value"])

    # Year average
    data["year"] = data["date"].dt.year
    year_avg = (
        data.groupby(["currency_id", "year"])["value"].mean().reset_index()
    )
    year_avg["date"] = pd.to_datetime(year_avg[["year"]].assign(month=1, day=1))
    year_avg["date"] = year_avg["date"].apply(
        lambda x: Date(value=x, precision=DATE_PRECISION_YEAR).serialize()
    )
    CurrencyRate.objects.filter(date__precision=DATE_PRECISION_YEAR).delete()
    bulk_create_from_df(CurrencyRate, year_avg, columns)

    # Month average
    data["month"] = data["date"].dt.month
    month_avg = (
        data.groupby(["currency_id", "year", "month"])["value"]
        .mean()
        .reset_index()
    )
    month_avg["date"] = pd.to_datetime(
        month_avg[["year", "month"]].assign(day=1)
    )
    month_avg["date"] = month_avg["date"].apply(
        lambda x: Date(value=x, precision=DATE_PRECISION_MONTH).serialize()
    )
    CurrencyRate.objects.filter(date__precision=DATE_PRECISION_MONTH).delete()
    bulk_create_from_df(CurrencyRate, month_avg, columns)
    logger.info("Successfully computed average currency rates.")


def update_currency_rates():
    """
    Update the currency rates to cover the Transfer timespan.

    TODO: Figure out the rate limit of the currency API and use a token
    bucket ?
    """
    logger.info("Updating currency rate data.")
    currencies = Currency.objects.all().values_list("id", flat=True)
    if len(currencies) == 0:
        logger.info("No currency to update.")
        return

    # Get the time period for which we need to fetch the rates.
    date_fields = [
        "date_invoice",
        "date_payment_recipient",
        "date_payment_emitter",
        "date_start",
        "date_end",
    ]
    t_extremas: DateExtremas = date_extremas_from_queryset(
        Transfer.objects.filter(amount__isnull=False), date_fields
    )[0]["_extremas"]
    if t_extremas.min is None:
        logger.info("No transfers to fetch currency rates for.")
        return

    # Make sure the interval spans full years so that we can make proper avg
    # rates.
    t_extremas.min = date(t_extremas.min.year, 1, 1)
    t_extremas.max = date(t_extremas.max.year, 12, 31)
    today = date.today()
    if t_extremas.max > today:
        t_extremas.max = today

    # Add 1 day because the last day is not included in the fetched interval.
    t_extremas.max += timedelta(days=1)
    t_extremas.min = date(t_extremas.min.year, 1, 1)

    # Fetch data for each currency individually
    c_extremas = date_extremas_from_queryset(
        CurrencyRate.objects.all(), ["date"], groupby=["currency_id"]
    )
    c_extremas = {c["currency_id"]: c["_extremas"] for c in c_extremas}
    for c in currencies:
        if c in c_extremas:
            continue
        c_extremas[c] = DateExtremas()

    for c_id, c_data in c_extremas.items():
        update_currency_rate(
            c_id,
            t_extremas,
            c_data,
        )


def compute_transfer_amounts():
    """
    Compute transfer amounts for all available currencies.

    The correct rate to use is derived according to the transfer's date
    precision.
    """
    logger.info("Computing transfer amounts in available currencies.")
    transfers = pd.DataFrame.from_records(
        Transfer.objects.filter(amount__isnull=False).values(
            "id", "amount", "date_clc", "currency_id"
        )
    )
    if transfers.empty:
        logger.info("No transfers to compute amounts for.")
        return
    rates = pd.DataFrame.from_records(
        CurrencyRate.objects.all().values("currency_id", "date", "value")
    )
    if rates.empty:
        logger.info("No currency rates to compute amounts.")
        return

    # This adds the columns date_value and date_precision
    date_extract = pd.json_normalize(rates["date"]).add_prefix("date_")
    rates = pd.concat([rates, date_extract], axis=1)

    rates["date_value"] = pd.to_datetime(rates["date_value"])
    rates["year"] = rates["date_value"].dt.year
    rates["month"] = rates["date_value"].dt.month
    rates["day"] = rates["date_value"].dt.day

    date_extract = pd.json_normalize(transfers["date_clc"]).add_prefix("date_")
    transfers = pd.concat([transfers, date_extract], axis=1)
    transfers["date_value"] = pd.to_datetime(transfers["date_value"])

    # Handle the transfers made after the last known rate differently
    max_date: datetime = rates["date_value"].max()
    t_future = transfers[transfers["date_value"] > max_date]

    transfers = transfers[~transfers.index.isin(t_future.index)]
    transfers["year"] = transfers["date_value"].dt.year
    transfers["month"] = transfers["date_value"].dt.month
    transfers["day"] = transfers["date_value"].dt.day
    t_year = transfers[
        transfers["date_precision"] == DATE_PRECISION_YEAR
    ].copy()
    t_month = transfers[
        transfers["date_precision"] == DATE_PRECISION_MONTH
    ].copy()
    t_day = transfers[transfers["date_precision"] == DATE_PRECISION_DAY].copy()

    currencies = rates["currency_id"].drop_duplicates().to_list()

    # 1 - Pivot the rate data to obtain currency rate columns per date
    r_pivot = (
        rates[
            ["date_precision", "year", "month", "day", "currency_id", "value"]
        ]
        .pivot_table(
            index=["date_precision", "year", "month", "day"],
            columns="currency_id",
            values="value",
            aggfunc="first",
        )
        .reset_index()
    )
    # 2 - Handle "future" transfers with the average rate over the last month
    last_known_rate = (
        r_pivot[r_pivot["date_precision"] == DATE_PRECISION_MONTH]
        .sort_values(["year", "month", "day"], ascending=False)
        .drop(columns=["year", "month", "day", "date_precision"])
        .head(1)
    )
    t_future = t_future.merge(last_known_rate, how="cross")

    # 3 - Add rate data to the transfer frame
    t_year = t_year.merge(
        r_pivot.drop(columns=["month", "day"]), on=["date_precision", "year"]
    )
    t_month = t_month.merge(
        r_pivot.drop(columns=["day"]),
        on=["date_precision", "year", "month"],
    )
    t_day = t_day.merge(
        r_pivot,
        on=["date_precision", "year", "month", "day"],
    )
    transfers = pd.concat([t_future, t_year, t_month, t_day], ignore_index=True)

    # 4 - Compute USD amount with appropriate rate
    for c in currencies:
        t_sub = transfers[transfers["currency_id"] == c]
        transfers.loc[t_sub.index, "amount_USD"] = t_sub["amount"] / t_sub[c]

    # 5 - Compute all other amounts based on USD one
    currency_cols = []
    for c in currencies:
        col_name = f"amount_{c}"
        currency_cols.append(col_name)
        transfers[col_name] = (
            (transfers["amount_USD"] * transfers[c]).round().astype("Int64")
        )

    # Dump results to the database
    transfers = transfers[["id", *currency_cols]].set_index("id")
    cols_rename = {c: c[-3:] for c in currency_cols}
    transfers.rename(columns=cols_rename, inplace=True)
    transfers["amounts_clc"] = transfers.to_dict(orient="index").values()
    transfers.reset_index(inplace=True)
    bulk_update_from_df(Transfer, transfers, ["id", "amounts_clc"])
    logger.info(
        "Successfully computed transfer amounts in available currencies."
    )


def currency_rates_workflow():
    """
    Execute the whole currency rate workflow:
        -   Update tha currency rates for all registered currencies.
        -   Compute the average rage for every date precision (day, month, year)
        -   Compute the converted amounts for every transfer.
    """
    logger.info("Starting currency rate workflow.")
    update_currency_rates()
    compute_average_rates()
    compute_transfer_amounts()
    logger.info("Ending currency rate workflow.")
    return TaskResult(partial=False)
