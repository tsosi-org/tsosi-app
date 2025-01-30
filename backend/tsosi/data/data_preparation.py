import logging
import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, ClassVar, Type

import pandas as pd
import pycountry
from tsosi.app_settings import app_settings
from tsosi.data.currencies.currency_rates import (
    SUPPORTED_CURRENCIES,
    check_currency,
)
from tsosi.models.date import (
    DATE_FORMAT,
    DATE_PRECISION_CHOICES,
    DATE_PRECISION_DAY,
    DATE_PRECISION_YEAR,
    Date,
    format_date,
)

from .exceptions import DataValidationError
from .utils import clean_null_values

logger = logging.getLogger(__name__)

CUSTOM_COUNTRY_MAPPING = {
    "USA": "United States",
    "Russia": "Russian Federation",
}
COUNTRY_NAME_MAPPING = {c.name: c for c in pycountry.countries}
COUNTRY_ALPHA_2_MAPPING = {c.alpha_2: c for c in pycountry.countries}


@dataclass(kw_only=True)
class ConstOrField:
    NAME: ClassVar[str]
    type: ClassVar[str] = "str"
    required: ClassVar[bool] = False
    constant: str | None = None
    field: str | None = None

    default: Any = None
    format: str | None = None
    date_precision: str | None = None

    def __post_init__(self):
        if self.constant is not None and self.field is not None:
            raise ValueError("You can set only one of `constant` and `field`")

        self.active = self.constant is not None or self.field is not None
        if (
            self.date_precision is not None
            and self.date_precision not in DATE_PRECISION_CHOICES.keys()
        ):
            raise ValueError(
                f"Wrong value for `date_precision`: {self.date_precision}. Available options are {DATE_PRECISION_CHOICES.keys()}"
            )


@dataclass(kw_only=True)
class FieldSource(ConstOrField):
    NAME = "source"
    required = True


@dataclass(kw_only=True)
class FieldAmount(ConstOrField):
    NAME = "amount"
    comma_decimal: bool = True
    required = True


@dataclass(kw_only=True)
class FieldCurrency(ConstOrField):
    NAME = "currency"


@dataclass(kw_only=True)
class FieldEmitterName(ConstOrField):
    NAME = "emitter_name"


@dataclass(kw_only=True)
class FieldEmitterRorId(ConstOrField):
    NAME = "emitter_ror_id"


@dataclass(kw_only=True)
class FieldEmitterWikidataId(ConstOrField):
    NAME = "emitter_wikidata_id"


@dataclass(kw_only=True)
class FieldEmitterUrl(ConstOrField):
    NAME = "emitter_url"
    type = "url"


@dataclass(kw_only=True)
class FieldEmitterCountry(ConstOrField):
    NAME = "emitter_country"
    type = "country"
    is_iso: bool = False


@dataclass(kw_only=True)
class FieldEmitterType(ConstOrField):
    NAME = "emitter_type"


@dataclass(kw_only=True)
class FieldRecipientName(ConstOrField):
    NAME = "recipient_name"


@dataclass(kw_only=True)
class FieldRecipientRorId(ConstOrField):
    NAME = "recipient_ror_id"


@dataclass(kw_only=True)
class FieldRecipientCountry(ConstOrField):
    NAME = "recipient_country"
    type = "country"
    is_iso: bool = False


@dataclass(kw_only=True)
class FieldRecipientWikidataId(ConstOrField):
    NAME = "recipient_wikidata_id"


@dataclass(kw_only=True)
class FieldRecipientUrl(ConstOrField):
    NAME = "recipient_url"
    type = "url"


@dataclass(kw_only=True)
class FieldConsortiumName(ConstOrField):
    NAME = "consortium_name"


@dataclass(kw_only=True)
class FieldConsortiumRorId(ConstOrField):
    NAME = "consortium_ror_id"


@dataclass(kw_only=True)
class FieldConsortiumWikidataId(ConstOrField):
    NAME = "consortium_wikidata_id"


@dataclass(kw_only=True)
class FieldConsortiumUrl(ConstOrField):
    NAME = "consortium_url"


@dataclass(kw_only=True)
class FieldConsortiumCountry(ConstOrField):
    NAME = "consortium_country"
    type = "country"
    is_iso: bool = False


@dataclass(kw_only=True)
class FieldDateAgreement(ConstOrField):
    NAME = "date_agreement"
    type = "date"


@dataclass(kw_only=True)
class FieldDateInvoice(ConstOrField):
    NAME = "date_invoice"
    type = "date"


@dataclass(kw_only=True)
class FieldDatePayment(ConstOrField):
    NAME = "date_payment"
    type = "date"


@dataclass(kw_only=True)
class FieldDateStart(ConstOrField):
    NAME = "date_start"
    type = "date"


@dataclass(kw_only=True)
class FieldDateEnd(ConstOrField):
    NAME = "date_end"
    type = "date"


@dataclass(kw_only=True)
class FieldOriginalId(ConstOrField):
    NAME = "original_id"


ALL_FIELDS: list[Type[ConstOrField]] = [
    FieldSource,
    FieldAmount,
    FieldCurrency,
    FieldEmitterName,
    FieldEmitterRorId,
    FieldEmitterWikidataId,
    FieldEmitterUrl,
    FieldEmitterCountry,
    FieldEmitterType,
    FieldRecipientName,
    FieldRecipientRorId,
    FieldRecipientWikidataId,
    FieldRecipientUrl,
    FieldRecipientCountry,
    FieldConsortiumName,
    FieldConsortiumUrl,
    FieldConsortiumRorId,
    FieldConsortiumWikidataId,
    FieldConsortiumCountry,
    FieldDateAgreement,
    FieldDateInvoice,
    FieldDatePayment,
    FieldDateStart,
    FieldDateEnd,
    FieldOriginalId,
]

DATE_FIELDS = [
    FieldDateAgreement,
    FieldDateInvoice,
    FieldDatePayment,
    FieldDateStart,
    FieldDateEnd,
]


@dataclass(kw_only=True)
class RawDataConfig:
    """
    Contains the config of the raw data to be processed.
    The main part consist of a mapping between the input data columns to our
    data-schema columns.
    """

    id: str
    # Input metadata
    input_type: str
    input_file_name: str

    # Field config data
    extract_currency_amount: bool = (
        False  # Extract currency and amount from a single column
    )
    fields: list[ConstOrField] = field(default_factory=list)

    # Additional optional metadata fields
    input_sheet_name: str | None = None
    year: int | None = None
    # List of date columns
    date_columns: list[str] = field(default_factory=list)

    # Calculated data
    organization_data: pd.DataFrame | None = None
    processed_data: pd.DataFrame | None = None

    def __post_init__(self):
        self.validate_fields()
        if self.year is None and self.no_date_field:
            raise ValueError("Either 1 date field or the year must be set.")

    def validate_fields(self):
        """
        Validate the given lists of fields.
        Maximum 1 field per field type.
        Amount and Source are mandatory.
        """
        present_field_types = []
        for f in self.fields:
            f_class = f.__class__
            if not f_class in ALL_FIELDS:
                raise ValueError(
                    f"Given field {f} is not a instance of the accepted fields."
                )
            if f_class in present_field_types:
                raise Exception(
                    f"2 fields of the same class {f_class} were passed."
                )
            present_field_types.append(f.__class__)

        for f_class in ALL_FIELDS:
            if not f_class.required:
                continue
            if not f_class in present_field_types:
                raise Exception(f"The field {f_class} is required.")

        if (
            not self.extract_currency_amount
            and not FieldCurrency in present_field_types
        ):
            raise Exception(
                f"The field `FieldCurrency` or `extract_currency_amout=True` is required."
            )

        missing_fields = [
            f_c for f_c in ALL_FIELDS if f_c not in present_field_types
        ]
        for f_c in missing_fields:
            self.fields.append(f_c())

    def get_field[T: ConstOrField](self, f_class: Type[T]) -> T:
        for f in self.fields:
            if f.__class__ == f_class:
                return f
        raise Exception(f"Field with class {f_class} not found.")

    def get_field_from_name(self, name: str):
        return next((f for f in self.fields if f.field == name), None)

    @property
    def active_fields(self) -> list[ConstOrField]:
        return [f for f in self.fields if f.active]

    @property
    def date_fields(self) -> list[ConstOrField]:
        return [self.get_field(f_c) for f_c in DATE_FIELDS]

    @property
    def no_date_field(self) -> bool:
        return all(f.active is False for f in self.date_fields)


# All configs
CONFIG_PCI = {
    "id": "pci",
    "extract_currency_amount": True,
    "fields": [
        FieldAmount(field="Amount"),
        FieldCurrency(default="EUR"),
        FieldRecipientName(constant="Peer Community In"),
        FieldRecipientRorId(constant="0315saa81"),
        FieldEmitterName(field="From organization"),
        FieldEmitterType(field="Category"),
        FieldEmitterUrl(field="Website"),
        FieldDatePayment(
            field="Year", format="%Y", date_precision=DATE_PRECISION_YEAR
        ),
    ],
}

CONFIG_SCIPOST = {
    "id": "scipost",
    "fields": [
        FieldRecipientName(constant="SciPost"),
        FieldRecipientWikidataId(constant="Q52663237"),
        FieldEmitterName(field="organization_name"),
        FieldEmitterCountry(field="organization_country", is_iso=True),
        FieldEmitterRorId(field="organization_ror_id"),
        FieldEmitterType(field="organization_orgtype"),
        FieldAmount(field="amount"),
        FieldCurrency(constant="EUR"),
        FieldDateStart(
            field="date_from",
            format="%Y-%m-%d",
            date_precision=DATE_PRECISION_YEAR,
        ),
        FieldDateEnd(
            field="date_until",
            format="%Y-%m-%d",
            date_precision=DATE_PRECISION_YEAR,
        ),
    ],
}

CONFIG_OPERAS = {
    "id": "operas",
    "fields": [
        FieldRecipientName(constant="OPERAS"),
        FieldRecipientRorId(constant="00rfexj26"),
        FieldEmitterName(field="Emitter"),
        FieldEmitterCountry(field="Country"),
        FieldAmount(field="Value"),
        FieldCurrency(field="Currency"),
        FieldDatePayment(
            field="Date", format="%Y", date_precision=DATE_PRECISION_YEAR
        ),
    ],
}

CONFIG_DOAJ_2021 = {
    "id": "doaj_2021",
    "fields": [
        FieldRecipientName(constant="Directory of Open Access Journals"),
        FieldRecipientRorId(constant="05amyt365"),
        FieldEmitterName(field="Institution name"),
        FieldEmitterCountry(field="country"),
        FieldAmount(field="amount"),
        FieldCurrency(field="currency"),
        FieldDateInvoice(
            constant=Date(
                value=date(year=2021, month=1, day=1),
                precision=DATE_PRECISION_YEAR,
            ).serialize()
        ),
    ],
}

CONFIG_DOAJ_2022 = {
    "id": "doaj_2022",
    "fields": [
        FieldRecipientName(constant="Directory of Open Access Journals"),
        FieldRecipientRorId(constant="05amyt365"),
        FieldEmitterName(field="Institution name"),
        FieldEmitterCountry(field="country"),
        FieldAmount(field="amount"),
        FieldCurrency(field="currency"),
        FieldDateInvoice(
            constant=Date(
                value=date(year=2022, month=1, day=1),
                precision=DATE_PRECISION_YEAR,
            ).serialize()
        ),
    ],
}

CONFIG_DOAJ_2023 = {
    "id": "doaj_2023",
    "fields": [
        FieldRecipientName(constant="Directory of Open Access Journals"),
        FieldRecipientRorId(constant="05amyt365"),
        FieldEmitterName(field="Institution name"),
        FieldEmitterCountry(field="country"),
        FieldAmount(field="amount"),
        FieldCurrency(field="currency"),
        FieldDateInvoice(
            constant=Date(
                value=date(year=2023, month=1, day=1),
                precision=DATE_PRECISION_YEAR,
            ).serialize()
        ),
    ],
}

CONFIG_DOAJ_2024 = {
    "id": "doaj_2024",
    "date_columns": ["Invoice date", "Support end date", "Paid up until"],
    "fields": [
        FieldRecipientName(constant="Directory of Open Access Journals"),
        FieldRecipientRorId(constant="05amyt365"),
        FieldEmitterName(field="Company"),
        FieldEmitterCountry(field="Country", is_iso=False),
        FieldAmount(field="Support amount"),
        FieldCurrency(field="Currency"),
        FieldConsortiumName(field="Agent"),
        FieldDateInvoice(
            field="Invoice date",
            format="%d/%m/%Y",
            default=Date(
                value=date(year=2024, month=1, day=1),
                precision=DATE_PRECISION_YEAR,
            ).serialize(),
            date_precision=DATE_PRECISION_DAY,
        ),
    ],
}

CONFIG_DOAJ_PUBLISHER_2024 = {
    "id": "doaj_publisher_2024",
    "fields": [
        FieldRecipientName(constant="Directory of Open Access Journals"),
        FieldRecipientRorId(constant="05amyt365"),
        FieldEmitterName(field="Company"),
        FieldEmitterUrl(field="emitter_website"),
        FieldEmitterRorId(field="emitter_ror_id"),
        FieldEmitterWikidataId(field="emitter_wikidata_id"),
        FieldEmitterCountry(field="Country"),
        FieldAmount(field="Support amount"),
        FieldCurrency(field="Currency"),
        FieldDateInvoice(
            constant=Date(
                value=date(year=2024, month=1, day=1),
                precision=DATE_PRECISION_YEAR,
            ).serialize()
        ),
    ],
}
CONFIG_DOAJ_PUBLISHER_2023 = {
    "id": "doaj_publisher_2023",
    "fields": [
        FieldRecipientName(constant="Directory of Open Access Journals"),
        FieldRecipientRorId(constant="05amyt365"),
        FieldEmitterName(field="Institution name"),
        FieldEmitterUrl(field="emitter_website"),
        FieldEmitterRorId(field="emitter_ror_id"),
        FieldEmitterWikidataId(field="emitter_wikidata_id"),
        FieldEmitterCountry(field="country"),
        FieldAmount(field="amount"),
        FieldCurrency(field="currency"),
        FieldDateInvoice(
            constant=Date(
                value=date(year=2023, month=1, day=1),
                precision=DATE_PRECISION_YEAR,
            ).serialize()
        ),
    ],
}
CONFIG_DOAJ_PUBLISHER_2022 = {
    "id": "doaj_publisher_2022",
    "fields": [
        FieldRecipientName(constant="Directory of Open Access Journals"),
        FieldRecipientRorId(constant="05amyt365"),
        FieldEmitterName(field="Institution name"),
        FieldEmitterUrl(field="emitter_website"),
        FieldEmitterRorId(field="emitter_ror_id"),
        FieldEmitterWikidataId(field="emitter_wikidata_id"),
        FieldEmitterCountry(field="country"),
        FieldAmount(field="amount"),
        FieldCurrency(field="currency"),
        FieldDateInvoice(
            constant=Date(
                value=date(year=2022, month=1, day=1),
                precision=DATE_PRECISION_YEAR,
            ).serialize()
        ),
    ],
}
CONFIG_DOAJ_PUBLISHER_2021 = {
    "id": "doaj_publisher_2021",
    "fields": [
        FieldRecipientName(constant="Directory of Open Access Journals"),
        FieldRecipientRorId(constant="05amyt365"),
        FieldEmitterName(field="Institution name"),
        FieldEmitterUrl(field="emitter_website"),
        FieldEmitterRorId(field="emitter_ror_id"),
        FieldEmitterWikidataId(field="emitter_wikidata_id"),
        FieldEmitterCountry(field="country"),
        FieldAmount(field="amount"),
        FieldCurrency(field="currency"),
        FieldDateInvoice(
            constant=Date(
                value=date(year=2021, month=1, day=1),
                precision=DATE_PRECISION_YEAR,
            ).serialize()
        ),
    ],
}

CONFIGS = [
    CONFIG_SCIPOST,
    CONFIG_PCI,
    CONFIG_OPERAS,
    CONFIG_DOAJ_2024,
    CONFIG_DOAJ_2023,
    CONFIG_DOAJ_2022,
    CONFIG_DOAJ_2021,
    CONFIG_DOAJ_PUBLISHER_2021,
    CONFIG_DOAJ_PUBLISHER_2022,
    CONFIG_DOAJ_PUBLISHER_2023,
    CONFIG_DOAJ_PUBLISHER_2024,
]

FILE_TYPES = [".xlsx", ".xls", ".json"]


def get_input_config(
    name: str, file_name: str, sheet_name: str | None = None
) -> RawDataConfig:
    config_mapping = {c["id"]: c for c in CONFIGS}
    if name not in config_mapping.keys():
        raise ValueError(
            f"Config {name} is not supported. "
            f"Available config options are: {list(config_mapping.keys())}."
        )
    file_path = app_settings.TSOSI_APP_TO_INGEST_DIR / file_name
    if not file_path.exists() or not file_path.is_file():
        raise ValueError(
            f"The provided file path {file_path} does not exist "
            "or is not accessible."
        )
    input_type = file_path.suffix
    if input_type not in FILE_TYPES:
        raise ValueError(
            f"File extension {input_type} is not supported. "
            f"Supported types are: {FILE_TYPES}."
        )
    input_type = ".xlsx" if input_type == ".xls" else input_type

    config = deepcopy(config_mapping[name])
    if input_type == ".xlsx":
        if sheet_name is None:
            raise ValueError(
                f"The sheet name is mandatory for spreadsheet input."
            )
        config["input_sheet_name"] = sheet_name

    config["input_type"] = input_type
    config["input_file_name"] = str(file_path)

    source_str = f"{name.capitalize()} - {file_path.name}"
    config["fields"].append(FieldSource(constant=source_str))
    return RawDataConfig(**config)


# Field names for the output dataframe
FIELD_RAW_DATA = "raw_data"
ORIGINAL_ID = "id_original"
ORIGINAL_TYPE = "type_original"


CURRENCY_MAPPING = {
    "€": "EUR",
    "£": "GBP",
    "$": "USD",
}


def currency_iso_from_value[T](val: T, error: bool = False) -> str | None:
    """
    According to the current data, the currency is always represented either by
    its symbol ("$", "£" or "€") or it contains the ISO code with other parasite
    inputs.
    """
    if val is None:
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
        if value in SUPPORTED_CURRENCIES:
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


def country_check_iso[T](val: T, error: bool = False) -> None:
    """
    Check that the provided value is a country ISO code.
    """
    if (
        val is not None
        and isinstance(val, str)
        and val in COUNTRY_ALPHA_2_MAPPING.keys()
    ):
        return
    elif val is None:
        return None
    msg = f"The provided country ISO code `{val}` does not exist."
    if error:
        raise DataValidationError(msg)
    logger.error(msg)


def country_iso_from_name[T](val: T, error: bool = False) -> str | None:
    """
    Get the country iso 3166-1 alpha-2 code from the input name.
    """
    if val is None:
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
        return results[0].alpha_2
    except LookupError:
        pass
    # if val in COUNTRY_NAME_MAPPING.keys():
    #     return COUNTRY_NAME_MAPPING[val].alpha_2
    msg = f"The provided country name `{val}` is non-standard."
    if error:
        raise DataValidationError(msg)
    logger.error(msg)
    return None


def country_name_from_iso[T](code: T) -> T:
    """
    Returns the country name of the given iso 3166-1 alpha-2 code.
    """
    if not isinstance(code, str):
        return code
    if code in COUNTRY_ALPHA_2_MAPPING.keys():
        return COUNTRY_ALPHA_2_MAPPING[code].name
    logger.warning(f"The provided country ISO code `{code}` does not exist.")
    return code


def clean_url[T](s: T) -> T:
    """
    Add default protocol and remove trailing slash from URL string.
    """
    if not s or not isinstance(s, str):
        return s
    if not s.startswith("https://") and not s.startswith("http://"):
        s = f"https://{s}"
    if s[-1] == "/":
        s = s[:-1]
    return s


def clean_cell_value[T](s: T) -> T:
    """
    Clean the value from a spreadsheet cell:
    - Normalize spacing values.
    - Strip whitespaces.
    """
    if not s or not isinstance(s, str):
        return s
    return re.sub(r"\s+", " ", s).strip()


def clean_number_value[T](value: T, comma_decimal=False) -> T | float:
    """
    Clean a number value by casting in to a number type.
    If `comma_decimal` is true, replace commas by the "." character,
    else discard them.
    """
    if value is None or not isinstance(value, str):
        return value
    value = value.replace(",", ".") if comma_decimal else value.replace(",", "")
    return pd.to_numeric(value, errors="coerce")


def extract_currency_amount[
    T
](val, error: bool = False) -> tuple[int | float | str | None, str | None]:
    """
    Returns the tuple (amount, currency) from a single value.
    The return values are not treated in any way.
    If the amount is a string, it will only contain digits and
    "," and "." characters.
    """

    if isinstance(val, (int, float)):
        return val, None
    elif val is None:
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


def undate[T](x: T, date_format: str = DATE_FORMAT) -> T | str:
    """
    Return the string representation of the date/datetime input.
    """
    if isinstance(x, datetime) or isinstance(x, date):
        return x.strftime(date_format)
    return x


def prepare_data(
    config: RawDataConfig,
    error: bool = True,
) -> None:
    """
    Convert the input data to our data format and
    perform various data cleaning.

    :param config:  The config object, defining how to obtain the data
                    and how to process it.
    :param error:   Whether to raise error while cleaning the data. This should
                    be True when the data is prepared before ingestion.
    """
    logger.info(f"Preparing data with config `{config.id}`.")

    # Get raw data
    origin = ""
    if config.input_type == ".xlsx":
        xls = pd.ExcelFile(config.input_file_name)
        df = pd.read_excel(xls, config.input_sheet_name)
        origin = (
            f"{config.input_file_name.split("/")[-1]}_{config.input_sheet_name}"
        )
    elif config.input_type == ".json":
        df = pd.read_json(config.input_file_name, orient="records")
        origin = config.input_file_name.split("/")[-1]
    else:
        raise ValueError("Valid input types are 'xlsx' and 'json'")

    # Cast na values to None for correct json dumping.
    clean_null_values(df)
    # Cast dates to strings
    for col in config.date_columns:
        field = config.get_field_from_name(col)
        format = field.format if field and field.format else DATE_FORMAT
        df[col] = df[col].apply(lambda x: undate(x, format))

    df["raw_data"] = df.apply(lambda row: row.to_dict(), axis=1)

    # Rename columns to appropriate referenced names
    cols_to_rename = {"raw_data": FIELD_RAW_DATA}

    for field in config.active_fields:
        if not field.field:
            continue
        cols_to_rename[field.field] = field.NAME

    df = df.reset_index(drop=True).rename(columns=cols_to_rename)

    # Clean whitespaces in string cells.
    for col in df.columns:
        df[col] = df[col].apply(clean_cell_value)

    cols_to_export = list(cols_to_rename.values())

    # Data cleaning
    for f in config.active_fields:
        # Insert constant fields
        if f.constant and f.type != "date":
            df[f.NAME] = clean_cell_value(f.constant)
            cols_to_export.append(f.NAME)
        # Insert default
        elif f.field and f.default and f.type != "date":
            df[f.NAME] = df[f.NAME].fillna(clean_cell_value(f.default))

        # Type related curation
        # Clean URLs
        if f.type == "url" and f.field is not None:
            df[f.NAME] = df[f.NAME].apply(clean_url)
        # Convert country names to ISO code
        elif f.type == "country":
            if f.is_iso:
                df[f.NAME].apply(lambda x: country_check_iso(x, error=error))
            else:
                df[f.NAME] = df[f.NAME].apply(
                    lambda x: country_iso_from_name(x, error=error)
                )
        elif f.type == "date":
            if f.constant:
                df[f.NAME] = df.apply(
                    lambda x: clean_cell_value(f.constant), axis=1
                )
                cols_to_export.append(f.NAME)
                continue
            format = f.format if f.format else DATE_FORMAT
            df[f.NAME] = pd.to_datetime(
                df[f.NAME], format=format, utc=True, errors="raise"
            ).dt.date
            date_precision = (
                f.date_precision if f.date_precision else DATE_PRECISION_YEAR
            )
            df[f.NAME] = df[f.NAME].apply(
                lambda x: format_date(x, date_precision)
            )
            if f.default is not None:
                df[f.NAME] = df[f.NAME].apply(
                    lambda x: f.default if pd.isna(x) else x
                )

    # Special case of single column holding both amount and currency
    if config.extract_currency_amount:
        df[[FieldAmount.NAME, FieldCurrency.NAME]] = df[FieldAmount.NAME].apply(
            lambda val: pd.Series(extract_currency_amount(val, error=error))
        )
        cols_to_export.append(FieldCurrency.NAME)

        # Sets the default currency here if required. It wasn't handled before
        # as it did not have its separate column
        currency_default = config.get_field(FieldCurrency).default
        if currency_default:
            df[FieldCurrency.NAME] = df[FieldCurrency.NAME].fillna(
                clean_cell_value(currency_default)
            )

    # Parse amount
    df[FieldAmount.NAME] = df[FieldAmount.NAME].apply(
        lambda x: clean_number_value(
            x, config.get_field(FieldAmount).comma_decimal
        )
    )

    # Convert currency to ISO code.
    df[FieldCurrency.NAME] = df[FieldCurrency.NAME].apply(
        lambda x: currency_iso_from_value(x, error=error)
    )
    # Check currency validity
    df[FieldCurrency.NAME].dropna().apply(lambda x: check_currency(x))

    # Drop amount if no currency is specified
    mask = (
        df[FieldCurrency.NAME].isnull() & ~df[FieldAmount.NAME].isnull()
    ) | (~df[FieldCurrency.NAME].isnull() & df[FieldAmount.NAME].isnull())
    df_warn = df[mask]
    if not df_warn.empty:
        logger.warning(
            f"{len(df_warn)} items contain an amount without currency or "
            "a currency without an amount. "
            "They will be ingested without both amount and currency data with the current config."
        )
        df.loc[df_warn.index, FieldAmount.NAME] = None
        df.loc[df_warn.index, FieldCurrency.NAME] = None

    # Handle date from metadata, in case there is no date in the input data
    if config.no_date_field:
        df[FieldDatePayment.NAME] = date(year=config.year)
        cols_to_export.append(FieldDatePayment.NAME)

    # Drop all columns whose data will not be used anymore.
    cols_to_drop = [c for c in df.columns if c not in cols_to_export]
    df = df.drop(columns=cols_to_drop)

    # Create empty columns for every field not already present in the df
    cols_to_add = [f.NAME for f in config.fields if f.NAME not in df.columns]
    df.loc[:, cols_to_add] = None

    # Compute the `original_id` field for custom tracking.
    # The ulterior generated transfert ID is a random UUID..
    origin = re.sub(r"\s+", "_", origin.strip())
    df.loc[:, FieldOriginalId.NAME] = f"{origin}_" + df.index.astype(str)

    config.processed_data = df

    logger.info(f"Successfully prepared the data for config {config.id}")
