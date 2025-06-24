from datetime import date

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_YEAR


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="pci",
        full_data=True,
        data_load_name=file_path.split("/")[-1],
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "pci",
        ".xlsx",
        source,
        extract_currency_amount=True,
        fields=[
            rdc.FieldRecipientName(constant="Peer Community In"),
            rdc.FieldRecipientRorId(constant="0315saa81"),
            rdc.FieldEmitterName(field="From organization"),
            rdc.FieldEmitterCountry(field="Country"),
            rdc.FieldEmitterRorId(field="emitter_ror_id"),
            rdc.FieldEmitterWikidataId(field="emitter_wikidata_id"),
            rdc.FieldEmitterUrl(field="Website"),
            rdc.FieldEmitterType(field="Category"),
            rdc.FieldAmount(field="Amount"),
            rdc.FieldHideAmount(constant=False),
            rdc.FieldCurrency(default="EUR"),
            rdc.FieldAgentName(field="Via?"),
            rdc.FieldAgentRorId(field="agent_ror_id"),
            rdc.FieldAgentWikidataId(field="agent_wikidata_id"),
            rdc.FieldAgentUrl(field="agent_website"),
            rdc.FieldDatePaymentRecipient(
                field="Year",
                format="%Y",
                date_precision=DATE_PRECISION_YEAR,
            ),
        ],
        input_file_name=file_path,
        input_sheet_name=sheet_name,
    )
