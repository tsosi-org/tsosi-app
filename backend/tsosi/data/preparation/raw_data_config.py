import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from typing import Any, ClassVar, Type

import pandas as pd
from tsosi.app_settings import app_settings
from tsosi.data.currencies.currency_rates import check_currency
from tsosi.data.utils import clean_null_values
from tsosi.models.date import (
    DATE_FORMAT,
    DATE_PRECISION_CHOICES,
    DATE_PRECISION_YEAR,
    format_date,
)
from tsosi.models.static_data import DATA_SOURCES

from .cleaning_utils import (
    check_bool_value,
    check_ror_id,
    check_wikidata_id,
    clean_cell_value,
    clean_number_value,
    clean_url,
    country_check_iso,
    country_iso_from_name,
    currency_iso_from_value,
    extract_currency_amount,
    undate,
)

logger = logging.getLogger(__name__)

__all__ = [
    "RawDataConfig",
    "RawDataConfigFromFile",
    "ALL_FIELDS",
    "DATE_FIELDS",
    "FieldAmount",
    "FieldHideAmount",
    "FieldCurrency",
    "FieldEmitterName",
    "FieldEmitterRorId",
    "FieldEmitterWikidataId",
    "FieldEmitterCustomId",
    "FieldEmitterUrl",
    "FieldEmitterCountry",
    "FieldEmitterType",
    "FieldRecipientName",
    "FieldRecipientRorId",
    "FieldRecipientWikidataId",
    "FieldRecipientCustomId",
    "FieldRecipientUrl",
    "FieldRecipientCountry",
    "FieldAgentName",
    "FieldAgentUrl",
    "FieldAgentRorId",
    "FieldAgentWikidataId",
    "FieldAgentCustomId",
    "FieldAgentCountry",
    "FieldDateInvoice",
    "FieldDatePaymentRecipient",
    "FieldDatePaymentEmitter",
    "FieldDateStart",
    "FieldDateEnd",
    "FieldOriginalId",
    "FieldOriginalAmountField",
]

INPUT_FILE_TYPES = [".xlsx", ".xls", ".json"]


@dataclass(kw_only=True)
class ConstOrField:
    NAME: ClassVar[str]
    type: ClassVar[str] = "str"
    required: ClassVar[bool] = False
    check_func: ClassVar[str | None] = None
    constant: str | bool | None = None
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
class FieldAmount(ConstOrField):
    NAME = "amount"
    comma_decimal: bool = True


@dataclass(kw_only=True)
class FieldCurrency(ConstOrField):
    NAME = "currency"


@dataclass(kw_only=True)
class FieldEmitterName(ConstOrField):
    NAME = "emitter_name"
    required = True


@dataclass(kw_only=True)
class FieldEmitterRorId(ConstOrField):
    NAME = "emitter_ror_id"
    check_func = "ror_id"


@dataclass(kw_only=True)
class FieldEmitterWikidataId(ConstOrField):
    NAME = "emitter_wikidata_id"
    check_func = "wikidata_id"


@dataclass(kw_only=True)
class FieldEmitterCustomId(ConstOrField):
    NAME = "emitter_custom_id"


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
    required = True


@dataclass(kw_only=True)
class FieldRecipientRorId(ConstOrField):
    NAME = "recipient_ror_id"
    check_func = "ror_id"


@dataclass(kw_only=True)
class FieldRecipientCustomId(ConstOrField):
    NAME = "recipient_custom_id"


@dataclass(kw_only=True)
class FieldRecipientCountry(ConstOrField):
    NAME = "recipient_country"
    type = "country"
    is_iso: bool = False


@dataclass(kw_only=True)
class FieldRecipientWikidataId(ConstOrField):
    NAME = "recipient_wikidata_id"
    check_func = "wikidata_id"


@dataclass(kw_only=True)
class FieldRecipientUrl(ConstOrField):
    NAME = "recipient_url"
    type = "url"


@dataclass(kw_only=True)
class FieldAgentName(ConstOrField):
    NAME = "agent_name"


@dataclass(kw_only=True)
class FieldAgentRorId(ConstOrField):
    NAME = "agent_ror_id"
    check_func = "ror_id"


@dataclass(kw_only=True)
class FieldAgentWikidataId(ConstOrField):
    NAME = "agent_wikidata_id"
    check_func = "wikidata_id"


@dataclass(kw_only=True)
class FieldAgentCustomId(ConstOrField):
    NAME = "agent_custom_id"


@dataclass(kw_only=True)
class FieldAgentUrl(ConstOrField):
    NAME = "agent_url"


@dataclass(kw_only=True)
class FieldAgentCountry(ConstOrField):
    NAME = "agent_country"
    type = "country"
    is_iso: bool = False


@dataclass(kw_only=True)
class FieldDateInvoice(ConstOrField):
    NAME = "date_invoice"
    type = "date"


@dataclass(kw_only=True)
class FieldDatePaymentRecipient(ConstOrField):
    NAME = "date_payment_recipient"
    type = "date"


@dataclass(kw_only=True)
class FieldDatePaymentEmitter(ConstOrField):
    NAME = "date_payment_emitter"
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


@dataclass(kw_only=True)
class FieldRawData(ConstOrField):
    NAME = "raw_data"


@dataclass(kw_only=True)
class FieldOriginalAmountField(ConstOrField):
    NAME = "original_amount_field"


@dataclass(kw_only=True)
class FieldHideAmount(ConstOrField):
    NAME = "hide_amount"
    required = True
    type = "bool"


ALL_FIELDS: list[Type[ConstOrField]] = [
    FieldAmount,
    FieldHideAmount,
    FieldCurrency,
    FieldEmitterName,
    FieldEmitterRorId,
    FieldEmitterWikidataId,
    FieldEmitterCustomId,
    FieldEmitterUrl,
    FieldEmitterCountry,
    FieldEmitterType,
    FieldRecipientName,
    FieldRecipientRorId,
    FieldRecipientWikidataId,
    FieldRecipientCustomId,
    FieldRecipientUrl,
    FieldRecipientCountry,
    FieldAgentName,
    FieldAgentUrl,
    FieldAgentRorId,
    FieldAgentWikidataId,
    FieldAgentCustomId,
    FieldAgentCountry,
    FieldDateInvoice,
    FieldDatePaymentRecipient,
    FieldDatePaymentEmitter,
    FieldDateStart,
    FieldDateEnd,
    FieldOriginalId,
    FieldOriginalAmountField,
]

DATE_FIELDS = [
    FieldDateInvoice,
    FieldDatePaymentRecipient,
    FieldDatePaymentEmitter,
    FieldDateStart,
    FieldDateEnd,
]


@dataclass(kw_only=True)
class DataLoadSource:
    data_source_id: str
    data_load_name: str
    date_data_obtained: date
    year: int | None = None
    full_data: bool = False

    def __post_init__(self):
        """
        Handle date field to enable populating the dataclass from JSON.
        """
        if isinstance(self.date_data_obtained, str):
            self.date_data_obtained = date.fromisoformat(
                self.date_data_obtained
            )

    def serialize(self) -> dict:
        data = asdict(self)
        data["date_data_obtained"] = self.date_data_obtained.isoformat()
        return data


@dataclass(kw_only=True)
class DataIngestionConfig:
    date_generated: str
    source: DataLoadSource
    count: int
    data: list

    def serialize(self) -> dict:
        data = asdict(self)
        data["source"] = self.source.serialize()
        return data


class RawDataConfig:
    """
    Contains the config of the raw data to be processed.
    The main part consist of a mapping between the input data columns to our
    data-schema columns using `ConstOrField` instances.
    """

    def __init__(
        self,
        id: str,
        input_type: str,
        source: DataLoadSource,
        fields: list[ConstOrField] = list(),
        date_columns: list[str] = list(),
        extract_currency_amount: bool = False,
        input_file_name: str | None = None,
        input_sheet_name: str | None = None,
    ):

        self.id = id
        self.input_type = input_type
        self.input_file_name = input_file_name
        self.input_sheet_name = input_sheet_name
        self.source = source
        if self.source.data_source_id not in DATA_SOURCES:
            raise ValueError(
                f"Provided source {self.source.data_source_id} "
                "is not supported. "
                f"Supported sources are {DATA_SOURCES}"
            )
        self.fields = fields
        self.extract_currency_amount = extract_currency_amount
        self.date_columns = date_columns
        self.origin = ""
        self.validate_fields()

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
            FieldAmount in present_field_types
            and not self.extract_currency_amount
            and not FieldCurrency in present_field_types
        ):
            raise Exception(
                f"The field `FieldCurrency` or `extract_currency_amout=True` "
                "is required when a `FieldAmount` is active."
            )

        missing_fields = [
            f_c for f_c in ALL_FIELDS if f_c not in present_field_types
        ]
        for f_c in missing_fields:
            self.fields.append(f_c())

        if self.no_date_field:
            raise ValueError("At least 1 date field must be set given.")

    def get_field(self, f_class: Type[ConstOrField]) -> ConstOrField:
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

    def get_data(self) -> Any:
        """
        Method to populate the raw data.

        :returns:   The "raw" transfer data.
        """
        raise NotImplementedError()

    def pre_process(self, data: Any, error: bool = True) -> pd.DataFrame:
        """
        Hook to perform source-dependent pre-processing before undergoing
        the common processing pipeline.

        :param df:      The data to pre-process.
        :param error:   Whether to raise error while cleaning/preparing the
                        data.
        """
        return data

    def prepare_data(self, error: bool = True) -> pd.DataFrame:
        """
        Fetch and undergo the full data preparation process according to this
        config.

        :param error:   Whether to raise error while cleaning/preparing the
                        data.
        """
        data = self.get_data()
        pre_processed = self.pre_process(data, error=error)
        return self.process(pre_processed, error=error)

    def process(
        self,
        df: pd.DataFrame,
        error: bool = True,
    ) -> pd.DataFrame:
        """
        Convert the input data to our data format and
        perform various data cleaning.

        :param df:      The transfer DataFrame to prepare.
        :param error:   Whether to raise error while cleaning the data.
                        This should be True when the data is prepared
                        for ingestion.
        :returns:       The processed data.
        """
        logger.info(f"Preparing data with config `{self.id}`.")

        # Cast na values to None for correct json dumping.
        clean_null_values(df)
        # Cast dates to strings
        for col in self.date_columns:
            field = self.get_field_from_name(col)
            format = field.format if field and field.format else DATE_FORMAT
            df[col] = df[col].apply(lambda x: undate(x, format))

        df[FieldRawData.NAME] = df.apply(
            lambda row: row.dropna().to_dict(), axis=1
        )
        amount_field = self.get_field(FieldAmount)
        df[FieldOriginalAmountField.NAME] = (
            amount_field.field if amount_field.field else None
        )
        # Rename columns to appropriate referenced names
        cols_to_rename = {
            FieldRawData.NAME: FieldRawData.NAME,
            FieldOriginalAmountField.NAME: FieldOriginalAmountField.NAME,
        }

        for field in self.active_fields:
            if not field.field:
                continue
            cols_to_rename[field.field] = field.NAME

        df = df.reset_index(drop=True).rename(columns=cols_to_rename)

        # Clean whitespaces in string cells.
        for col in df.columns:
            df[col] = df[col].apply(clean_cell_value)

        cols_to_export = list(cols_to_rename.values())

        # Data cleaning
        for f in self.active_fields:
            # Insert constant fields
            if f.constant is not None and f.type != "date":
                # Trying to assign a dict value to every row is troublesome
                # with pandas
                if isinstance(f.constant, dict):
                    value = clean_cell_value(f.constant)
                    df[f.NAME] = df.apply(lambda x: value, axis=1)
                else:
                    df[f.NAME] = clean_cell_value(f.constant)
                cols_to_export.append(f.NAME)
            # Insert default
            elif f.field and f.default and f.type != "date":
                df[f.NAME] = df[f.NAME].fillna(clean_cell_value(f.default))

            # Type related curation
            # Clean URLs
            if f.type == "url" and f.field is not None:
                df[f.NAME] = df[f.NAME].apply(clean_url)
            # Boolean field should be set
            elif f.type == "bool":
                df[f.NAME].apply(lambda x: check_bool_value(x, error))

            # Convert country names to ISO code
            elif f.type == "country":
                if f.is_iso:  # type: ignore
                    df[f.NAME].apply(
                        lambda x: country_check_iso(x, error=error)
                    )
                else:
                    df[f.NAME] = df[f.NAME].apply(
                        lambda x: country_iso_from_name(x, error=error)
                    )
            elif f.type == "date":
                if f.constant:
                    value = clean_cell_value(f.constant)
                    df[f.NAME] = df.apply(lambda x: value, axis=1)
                    cols_to_export.append(f.NAME)
                    continue
                format = f.format if f.format else DATE_FORMAT
                df[f.NAME] = pd.to_datetime(
                    df[f.NAME], format=format, utc=True, errors="raise"
                ).dt.date
                date_precision = (
                    f.date_precision
                    if f.date_precision
                    else DATE_PRECISION_YEAR
                )
                df[f.NAME] = df[f.NAME].apply(
                    lambda x: format_date(x, date_precision)
                )
                if f.default is not None:
                    df[f.NAME] = df[f.NAME].apply(
                        lambda x: f.default if pd.isna(x) else x
                    )

            if f.check_func:
                if f.check_func == "ror_id":
                    df[f.NAME].apply(lambda x: check_ror_id(x, error))
                elif f.check_func == "wikidata_id":
                    df[f.NAME].apply(lambda x: check_wikidata_id(x, error))
                else:
                    raise ValueError(
                        f"`check_func` value {f.check_func} is not supported."
                    )

        # Special case of single column holding both amount and currency
        if self.extract_currency_amount:
            df[[FieldAmount.NAME, FieldCurrency.NAME]] = df[
                FieldAmount.NAME
            ].apply(
                lambda val: pd.Series(extract_currency_amount(val, error=error))
            )
            cols_to_export.append(FieldCurrency.NAME)

            # Sets the default currency here if required. It wasn't handled before
            # as it did not have its separate column
            currency_default = self.get_field(FieldCurrency).default
            if currency_default:
                df[FieldCurrency.NAME] = df[FieldCurrency.NAME].fillna(
                    clean_cell_value(currency_default)
                )

        # Parse amount
        df[FieldAmount.NAME] = df[FieldAmount.NAME].apply(
            lambda x: clean_number_value(
                x, self.get_field(FieldAmount).comma_decimal, error=error  # type: ignore
            )
        )

        # Convert currency to ISO code.
        df[FieldCurrency.NAME] = df[FieldCurrency.NAME].apply(
            lambda x: currency_iso_from_value(x, error=error)
        )
        # Check currency validity
        df[FieldCurrency.NAME].dropna().apply(
            lambda x: check_currency(x, error=error)
        )

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

        # TODO: Check identifiers syntax

        # Drop all columns whose data will not be used anymore.
        cols_to_drop = [c for c in df.columns if c not in cols_to_export]
        df = df.drop(columns=cols_to_drop)

        # Compute the `original_id` field for custom tracking.
        # The ulterior generated transfer ID is a random UUID..
        origin = re.sub(r"\s+", "_", self.origin.strip())
        df.loc[:, FieldOriginalId.NAME] = (  # type:ignore
            f"{origin}_" + df.index.astype(str)
        )

        self.processed_data = df

        logger.info(f"Successfully prepared the data for config {self.id}")
        clean_null_values(df)
        return df

    def generate_data_ingestion_config(self) -> DataIngestionConfig:
        """
        Generate the data ingestion config, ready to be processed by the
        ingestion pipeline.

        :returns:   The formatted DataIngestionConfig object.
        """
        data = self.prepare_data()
        return DataIngestionConfig(
            date_generated=datetime.now(UTC).isoformat(timespec="seconds"),
            source=self.source,
            count=len(data),
            data=data.sort_index(axis=1).to_dict(orient="records"),
        )

    def generate_data_file(self, output_folder=None):
        """
        Generate a data file in the TSOSI format, ready for ingestion.
        """
        ingestion_config = self.generate_data_ingestion_config()
        file_name = f"{date.today()}_{self.source.data_source_id}"
        if self.source.year:
            file_name += f"_{self.source.year}"
        if self.source.full_data:
            file_name += f"_full"
        file_name += ".json"
        if output_folder is None:
            output_folder = app_settings.DATA_EXPORT_FOLDER
        file_path = output_folder / file_name
        with open(file_path, "w") as f:
            json.dump(ingestion_config.serialize(), f, indent=2)

        logger.info(f"Successfully write TSOSI data file at {file_path}")


class RawDataConfigFromFile(RawDataConfig):
    """
    Raw data config that populates its data from a file.
    """

    input_file_name: str

    def __init__(self, *args, **kwargs):
        if kwargs.get("input_file_name") is None:
            raise ValueError("`input_file_name` is required ")
        super().__init__(*args, **kwargs)

    def get_data(self) -> pd.DataFrame:
        if self.input_type in [".xlsx", ".xls"]:
            if self.input_sheet_name is None:
                raise ValueError(
                    "You must input a `input_sheet_name` "
                    "when populating data from a spreadsheet."
                )
            xls = pd.ExcelFile(self.input_file_name)
            df = pd.read_excel(xls, self.input_sheet_name)
            self.origin = (
                f"{self.input_file_name.split("/")[-1]}_{self.input_sheet_name}"
            )
        elif self.input_type == ".json":
            df = pd.read_json(self.input_file_name, orient="records")
            self.origin = self.input_file_name.split("/")[-1]
        else:
            raise ValueError(
                f"Invalid input type: {self.input_type}. "
                f"Supported input types are {INPUT_FILE_TYPES}"
            )
        return df


def create_missing_fields(df: pd.DataFrame):
    """
    Create empty columns for every input field not already present in the
    given dataframe.
    """
    cols_to_add = [f.NAME for f in ALL_FIELDS if f.NAME not in df.columns]
    df.loc[:, cols_to_add] = None
    clean_null_values(df)
