from datetime import date
from pathlib import Path

from tsosi.data.preparation import raw_data_config as rdc


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="rotterdam",
        entity_id="057w15z03",
        full_data=True,
        data_load_name=Path(file_path).name,
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "rotterdam",
        ".xlsx",
        source,
        input_file_name=file_path,
        input_sheet_name=sheet_name,
        fields=[
            rdc.FieldEmitterName(constant="Erasmus University Rotterdam"),
            rdc.FieldEmitterRorId(constant="057w15z03"),
            rdc.FieldRecipientName(field="recipient/name"),
            rdc.FieldRecipientRorId(field="recipient/ror_id"),
            rdc.FieldRecipientWikidataId(field="recipient/wikidata_id"),
            rdc.FieldRecipientCustomId(field="recipient/custom_id"),
            rdc.FieldAgentName(field="intermediary/name"),
            rdc.FieldAgentRorId(field="intermediary/ror_id"),
            rdc.FieldAgentWikidataId(field="intermediary/wikidata_id"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldHideAmount(constant=False),
            rdc.FieldCurrency(field="currency"),
            rdc.FieldDatePaymentRecipient(field="date_received"),
            rdc.FieldDatePaymentEmitter(field="date_sent"),
            rdc.FieldDateInvoice(field="date_invoice"),
            rdc.FieldDateStart(field="contract/date_start"),
            rdc.FieldDateEnd(field="contract/date_end"),
            rdc.FieldSupportType(field="support_type"),
        ],
    )
