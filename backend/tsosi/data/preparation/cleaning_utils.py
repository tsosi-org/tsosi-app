import logging
import re
from datetime import date, datetime
from typing import Any

import pandas as pd
import pycountry
from tsosi.data.exceptions import DataValidationError
from tsosi.data.pid_registry.ror import ROR_ID_REGEX
from tsosi.data.pid_registry.wikidata import WIKIDATA_ID_REGEX
from tsosi.models.date import DATE_FORMAT

logger = logging.getLogger(__name__)

CUSTOM_COUNTRY_MAPPING = {
    "USA": "United States",
    "Russia": "Russian Federation",
}
COUNTRY_NAME_MAPPING = {c.name: c for c in pycountry.countries}  # type:ignore
COUNTRY_ALPHA_2_MAPPING = {
    c.alpha_2: c for c in pycountry.countries  # type:ignore
}


# Field names for the output dataframe
FIELD_RAW_DATA = "raw_data"

CURRENCY_MAPPING = {
    "€": "EUR",
    "£": "GBP",
    "$": "USD",
}


def currency_iso_from_value(val, error: bool = False) -> str | None:
    """
    According to the current data, the currency is always represented either by
    its symbol ("$", "£" or "€") or it contains the ISO code with other parasite
    inputs.
    """
    if pd.isna(val):
        return None
    if not isinstance(val, str):
        msg = f"Currency ISO code could not be derived from input value `{val}`"
        if error:
            raise DataValidationError(msg)
        logger.error(msg)
        return None

    match = re.search(r"[A-Z]{3}", val)
    if match:
        value = match.group(0)
        return value

    # We manually map currency symbols (€, $ and £) to occidental currencies..
    # Not very good.
    for symbol, code in CURRENCY_MAPPING.items():
        if symbol in val:
            return code

    msg = f"Currency ISO code could not be derived from input value `{val}`"
    if error:
        raise DataValidationError(msg)
    logger.error(msg)
    return None


def country_check_iso(val, error: bool = False) -> None:
    """
    Check that the provided value is a country ISO code.
    """
    if isinstance(val, str) and val in COUNTRY_ALPHA_2_MAPPING.keys():
        return
    elif pd.isna(val):
        return None
    msg = f"The provided country ISO code `{val}` does not exist."
    if error:
        raise DataValidationError(msg)
    logger.error(msg)


def country_iso_from_name(val, error: bool = False) -> str | None:
    """
    Get the country iso 3166-1 alpha-2 code from the input name.
    """
    if pd.isna(val):
        return None
    elif not isinstance(val, str):
        msg = f"The provided country name `{val}` is not valid."
        if error:
            raise DataValidationError(msg)
        logger.error(msg)
        return None
    val = CUSTOM_COUNTRY_MAPPING.get(val, val)

    try:
        results = pycountry.countries.search_fuzzy(val)
        return results[0].alpha_2  # type: ignore
    except LookupError:
        pass
    msg = f"The provided country name `{val}` is non-standard."
    if error:
        raise DataValidationError(msg)
    logger.error(msg)
    return None


def country_name_from_iso[T: Any](code: T) -> T | str:
    """
    Returns the country name of the given iso 3166-1 alpha-2 code.
    """
    if not isinstance(code, str):
        return code
    if code in COUNTRY_ALPHA_2_MAPPING.keys():
        return COUNTRY_ALPHA_2_MAPPING[code].name  # type: ignore
    logger.warning(f"The provided country ISO code `{code}` does not exist.")
    return code


def clean_url[T: Any](s: T) -> T | str:
    """
    Add default protocol and remove trailing slash from URL string.
    """
    if not isinstance(s, str):
        return s
    res = s
    if not res.startswith("https://") and not res.startswith("http://"):
        res = f"https://{res}"
    if res[-1] == "/":
        res = res[:-1]
    return res


def clean_cell_value[T: Any](s: T) -> T | str:
    """
    Clean the value from a spreadsheet cell:
    - Normalize spacing values.
    - Strip whitespaces.
    """
    if not isinstance(s, str):
        return s
    return re.sub(r"\s+", " ", s).strip()


def clean_number_value[
    T: Any
](value: T, comma_decimal=False, error=False) -> T | float:
    """
    Clean a number value by casting in to a number type.
    If `comma_decimal` is true, replace commas by the "." character,
    else discard them.
    """
    if not isinstance(value, str):
        return value
    res = clean_cell_value(value).replace(" ", "")
    res = res.replace(",", ".") if comma_decimal else res.replace(",", "")
    return pd.to_numeric(res, errors="raise" if error else "coerce")


def extract_currency_amount(
    val, error: bool = False
) -> tuple[int | float | str | None, str | None]:
    """
    Returns the tuple (amount, currency) from a single value.
    The return values are not treated in any way.
    If the amount is a string, it will only contain digits and
    "," and "." characters.
    """

    if isinstance(val, (int, float)):
        return val, None
    elif pd.isna(val) is None:
        return None, None
    elif not isinstance(val, str):
        msg = f"Could not parse currency and amount from `{val}`"
        if error:
            raise DataValidationError(msg)
        logger.error(msg)
        return None, None

    match = re.match(r"([^0-9]*)([0-9]+[\s0-9.,]*)([^0-9]*)", val)
    amount, currency = None, None
    if match:
        amount = match.group(2)
        amount = re.sub(r"\s+", "", amount)
        if match.group(1):
            currency = clean_cell_value(match.group(1))
        if match.group(3):
            currency = clean_cell_value(
                match.group(3)
                if not currency
                else f"{currency} {match.group(3)}"
            )
    if amount is None:
        msg = f"Could not parse currency and amount from `{val}`"
        if error:
            raise DataValidationError(msg)
        logger.error(msg)
    return amount, currency


def undate[T: Any](x: T, date_format: str = DATE_FORMAT) -> T | str:
    """
    Return the string representation of the date/datetime input.
    """
    if isinstance(x, datetime) or isinstance(x, date):
        return x.strftime(date_format)
    return x


def check_regex(value, regex: re.Pattern | str, error: bool = False) -> bool:
    """
    Check whether the provided value matches the given regex.
    """
    if pd.isna(value):
        return True
    if not isinstance(value, str):
        if error:
            raise DataValidationError(f"Wrong value for regex {regex}: {value}")
        return False
    if re.search(regex, value):
        return True

    if error:
        raise DataValidationError(f"Wrong value for regex {regex}: {value}")
    return False


def check_ror_id(value, error: bool = False) -> bool:
    return check_regex(value, ROR_ID_REGEX, error)


def check_wikidata_id(value, error: bool = False) -> bool:
    return check_regex(value, WIKIDATA_ID_REGEX, error)


def check_bool_value(value, error: bool = False) -> bool:
    if isinstance(value, bool):
        return True
    if error:
        raise DataValidationError(f"Wrong boolean value: {value}")
    return False
