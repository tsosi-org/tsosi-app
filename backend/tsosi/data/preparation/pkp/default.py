from datetime import date

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_MONTH


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="pkp",
        entity_id="05ek4tb53",
        full_data=True,
        data_load_name=file_path.split("/")[-1],
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "pkp",
        ".xlsx",
        source,
        extract_currency_amount=False,
        input_file_name=file_path,
        input_sheet_name=sheet_name,
        fields=[
            rdc.FieldRecipientName(constant="Public Knowledge Project"),
            rdc.FieldRecipientRorId(constant="05ek4tb53"),
            rdc.FieldEmitterName(field="emitter/name"),
            rdc.FieldEmitterRorId(field="emitter/ror_id"),
            rdc.FieldEmitterWikidataId(field="emitter/wikidata_id"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldCurrency(field="currency"),
            rdc.FieldHideAmount(constant=True),
            rdc.FieldAgentName(field="agent/name"),
            rdc.FieldAgentRorId(field="agent/ror_id"),
            rdc.FieldAgentWikidataId(field="agent/wikidata_id"),
            # rdc.FieldDateInvoice(
            #     field="date_invoice",
            #     format="%m/%Y",
            #     date_precision=DATE_PRECISION_MONTH,
            # ),
            rdc.FieldDateStart(
                field="date_start",
                format="%m/%Y",
                date_precision=DATE_PRECISION_MONTH,
            ),
            rdc.FieldDateEnd(
                field="date_end",
                format="%m/%Y",
                date_precision=DATE_PRECISION_MONTH,
            ),
        ],
    )
