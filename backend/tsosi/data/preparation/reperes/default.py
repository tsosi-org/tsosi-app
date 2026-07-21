from datetime import date
from pathlib import Path

from tsosi.data.preparation import raw_data_config as rdc


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="reperes",
        full_data=True,
        data_load_name=Path(file_path).name,
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "reperes",
        ".xlsx",
        source,
        fields=[
            rdc.FieldRecipientName(constant="Repères"),
            rdc.FieldRecipientWikidataId(constant="Q117355383"),
            rdc.FieldEmitterName(field="emitter/name"),
            rdc.FieldEmitterWikidataId(field="emitter/wikidata_id"),
            rdc.FieldSupportType(field="support_type"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldHideAmount(constant=False),
            rdc.FieldCurrency(field="currency"),
            rdc.FieldDatePaymentRecipient(field="date_received"),
        ],
        input_file_name=file_path,
        input_sheet_name=sheet_name,
    )
