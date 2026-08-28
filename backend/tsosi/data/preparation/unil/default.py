from datetime import date
from pathlib import Path

from tsosi.data.preparation import raw_data_config as rdc


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="unil",
        entity_id="019whta54",
        full_data=True,
        data_load_name=Path(file_path).name,
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "unil",
        ".xlsx",
        source,
        input_file_name=file_path,
        input_sheet_name=sheet_name,
        fields=[
            rdc.FieldEmitterName(constant="University of Lausanne"),
            rdc.FieldEmitterRorId(constant="019whta54"),
            # rdc.FieldAgentName(field="intermediary/name"),
            # rdc.FieldAgentRorId(field="intermediary/ror_id"),
            # rdc.FieldAgentWikidataId(field="intermediary/wikidata_id"),
            # rdc.FieldAgentCustomId(field="intermediary/custom_id"),
            rdc.FieldRecipientName(field="recipient/name"),
            rdc.FieldRecipientRorId(field="recipient/ror_id"),
            rdc.FieldRecipientWikidataId(field="recipient/wikidata_id"),
            rdc.FieldRecipientCustomId(field="recipient/custom_id"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldCurrency(field="currency"),
            rdc.FieldHideAmount(constant=False),
            rdc.FieldDateInvoice(field="date_invoice"),
            rdc.FieldDatePaymentEmitter(field="date_emitter"),
            rdc.FieldDatePaymentRecipient(field="date_received"),
            rdc.FieldDateStart(field="contract/date_start"),
            rdc.FieldDateEnd(field="contract/date_end"),
        ],
    )
