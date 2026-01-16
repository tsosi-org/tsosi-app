from datetime import date
from pathlib import Path

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_DAY


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="uga",
        entity_id="02rx3b187",
        full_data=True,
        data_load_name=Path(file_path).name,
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "uga",
        ".xlsx",
        source,
        input_file_name=file_path,
        input_sheet_name=sheet_name,
        fields=[
            rdc.FieldEmitterName(constant="UGA"),
            rdc.FieldEmitterRorId(constant="02rx3b187"),
            rdc.FieldEmitterSub(field="sub_institution"),
            rdc.FieldRecipientName(field="infrastructure"),
            rdc.FieldRecipientRorId(field="infrastructure/ror_id"),
            rdc.FieldRecipientWikidataId(field="infrastructure/wikidata_id"),
            rdc.FieldRecipientCustomId(field="infrastructure/custom_id"),
            rdc.FieldAgentName(field="intermediary"),
            rdc.FieldAgentRorId(field="intermediary/ror_id"),
            rdc.FieldAgentWikidataId(field="intermediary/wikidata_id"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldHideAmount(constant=False),
            rdc.FieldCurrency(constant="EUR"),
            rdc.FieldDatePaymentRecipient(field="date_received"),
            rdc.FieldDatePaymentEmitter(field="date_emitted"),
            rdc.FieldDateInvoice(field="date_invoice"),
        ],
    )
