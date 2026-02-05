from datetime import date
from pathlib import Path

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_DAY


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="uminho",
        entity_id="037wpkx04",
        full_data=True,
        data_load_name=Path(file_path).name,
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "uminho",
        ".xlsx",
        source,
        input_file_name=file_path,
        input_sheet_name=sheet_name,
        fields=[
            rdc.FieldEmitterName(constant="University of Minho"),
            rdc.FieldEmitterRorId(constant="037wpkx04"),
            rdc.FieldRecipientName(field="infrastructure/name"),
            rdc.FieldRecipientRorId(field="infrastructure/ror_id"),
            rdc.FieldRecipientWikidataId(field="infrastructure/wikidata_id"),
            rdc.FieldRecipientCustomId(field="infrastructure/custom_id"),
            rdc.FieldAgentName(field="intermediary/name"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldHideAmount(constant=False),
            rdc.FieldCurrency(field="currency"),
            rdc.FieldDatePaymentEmitter(field="date_emitted"),
        ],
    )
