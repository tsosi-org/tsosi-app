from datetime import date

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_YEAR


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="pci",
        entity_id="0315saa81",
        full_data=True,
        data_load_name=file_path.split("/")[-1],
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "pci",
        ".xlsx",
        source,
        extract_currency_amount=True,
        input_file_name=file_path,
        input_sheet_name=sheet_name,
        fields=[
            rdc.FieldRecipientName(constant="Peer Community In"),
            rdc.FieldRecipientRorId(constant="0315saa81"),
            rdc.FieldEmitterName(field="emitter/name"),
            rdc.FieldEmitterCountry(field="emitter/country"),
            rdc.FieldEmitterRorId(field="emitter/ror_id"),
            rdc.FieldEmitterWikidataId(field="emitter/wikidata_id"),
            rdc.FieldEmitterUrl(field="emitter/website"),
            rdc.FieldEmitterType(field="emitter/type"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldHideAmount(constant=False),
            rdc.FieldCurrency(default="EUR"),
            rdc.FieldAgentName(field="agent/name"),
            rdc.FieldAgentRorId(field="agent/ror_id"),
            rdc.FieldAgentWikidataId(field="agent/wikidata_id"),
            rdc.FieldAgentUrl(field="agent/website"),
            rdc.FieldDatePaymentRecipient(
                field="year",
                format="%Y",
                date_precision=DATE_PRECISION_YEAR,
            ),
        ],
    )
