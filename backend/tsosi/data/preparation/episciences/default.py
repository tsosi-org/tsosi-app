from datetime import date
from pathlib import Path

from tsosi.data.preparation import raw_data_config as rdc


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="episciences",
        entity_id="Q23688650",
        full_data=True,
        data_load_name=Path(file_path).name,
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "episciences",
        ".xlsx",
        source,
        input_file_name=file_path,
        input_sheet_name=sheet_name,
        fields=[
            rdc.FieldEmitterName(field="emitter/name"),
            rdc.FieldEmitterRorId(field="emitter/ror_id"),
            rdc.FieldEmitterWikidataId(field="emitter/wikidata_id"),
            rdc.FieldAgentName(field="intermediary/name"),
            rdc.FieldAgentRorId(field="intermediary/ror_id"),
            rdc.FieldAgentWikidataId(field="intermediary/wikidata_id"),
            rdc.FieldRecipientName(constant="Episciences"),
            rdc.FieldRecipientWikidataId(constant="Q23688650"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldHideAmount(constant=True),
            rdc.FieldCurrency(field="currency"),
            rdc.FieldDatePaymentRecipient(field="date_received"),
            rdc.FieldDatePaymentEmitter(field="date_sent"),
            rdc.FieldDateInvoice(field="date_invoice"),
            rdc.FieldDateStart(field="contract/date_start"),
            rdc.FieldDateEnd(field="contract/date_end"),
        ],
    )
