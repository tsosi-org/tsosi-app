from datetime import date

import pandas as pd
from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_DAY

from .data import get_scipost_raw_data, prepare_data

SCIPOST_CONFIG_FIELDS = [
    rdc.FieldRecipientName(constant="SciPost"),
    rdc.FieldRecipientWikidataId(constant="Q52663237"),
    rdc.FieldEmitterName(field="emitter"),
    rdc.FieldEmitterCountry(field="emitter_country", is_iso=True),
    rdc.FieldEmitterRorId(field="emitter_ror_id"),
    rdc.FieldEmitterWikidataId(field="emitter_wikidata_id"),
    rdc.FieldEmitterUrl(field="emitter_website_url"),
    rdc.FieldEmitterType(field="emitter_type"),
    rdc.FieldAmount(field="amount"),
    rdc.FieldHideAmount(field="hide_amount"),
    rdc.FieldCurrency(constant="EUR"),
    rdc.FieldDatePaymentRecipient(
        field="payment_date",
        format="%Y-%m-%d",
        date_precision=DATE_PRECISION_DAY,
    ),
    rdc.FieldDateInvoice(
        field="invoice_date",
        format="%Y-%m-%d",
        date_precision=DATE_PRECISION_DAY,
    ),
    rdc.FieldDateStart(
        field="subsidy_date_from",
        format="%Y-%m-%d",
        date_precision=DATE_PRECISION_DAY,
    ),
    rdc.FieldDateEnd(
        field="subsidy_date_until",
        format="%Y-%m-%d",
        date_precision=DATE_PRECISION_DAY,
    ),
    rdc.FieldAgentName(field="agent"),
    rdc.FieldAgentCountry(field="agent_country"),
    rdc.FieldAgentRorId(field="agent_ror_id"),
    rdc.FieldAgentWikidataId(field="agent_wikidata_id"),
    rdc.FieldAgentUrl(field="agent_website_url"),
]


def get_file_config(
    file_path: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="scipost",
        full_data=True,
        data_load_name=file_path.split("/")[-1],
        date_data_obtained=date_data,
        entity_id="05br64h13",
    )
    return rdc.RawDataConfigFromFile(
        "scipost_from_file",
        ".json",
        source,
        fields=SCIPOST_CONFIG_FIELDS,
        input_file_name=file_path,
    )


class ScipostRawDataConfigFromApi(rdc.RawDataConfig):
    """
    Automated raw data config for scipost.
    """

    def get_data(self) -> dict[str, pd.DataFrame]:
        self.origin = "scipost_api"
        return get_scipost_raw_data()

    def pre_process(
        self, data: dict[str, pd.DataFrame], error: bool = True
    ) -> pd.DataFrame:

        return prepare_data(
            data["payments"], data["subsidies"], data["collectives"]
        )


def get_api_config() -> ScipostRawDataConfigFromApi:
    source = rdc.DataLoadSource(
        data_source_id="scipost",
        full_data=True,
        data_load_name="scipost_api",
        date_data_obtained=date.today(),
        entity_id="05br64h13",
    )
    return ScipostRawDataConfigFromApi(
        "scipost_from_api", "api", source, fields=SCIPOST_CONFIG_FIELDS
    )
