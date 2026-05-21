from datetime import date
from pathlib import Path

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_DAY, DATE_PRECISION_YEAR


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="operas",
        entity_id="00rfexj26",
        full_data=True,
        data_load_name=Path(file_path).name,
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "operas",
        ".xlsx",
        source,
        fields=[
            rdc.FieldRecipientName(constant="OPERAS"),
            rdc.FieldRecipientRorId(constant="00rfexj26"),
            rdc.FieldEmitterName(field="emitter/name"),
            rdc.FieldEmitterCountry(field="country"),
            rdc.FieldEmitterRorId(field="emitter/ror_id"),
            rdc.FieldEmitterWikidataId(field="emitter/wikidata_id"),
            rdc.FieldEmitterCustomId(field="emitter/custom_id"),
            rdc.FieldEmitterSub(field="emitter/sub"),
            rdc.FieldSupportType(field="support_type"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldHideAmount(constant=False),
            rdc.FieldCurrency(constant="EUR"),
            rdc.FieldDatePaymentRecipient(field="date_received"),
        ],
        input_file_name=file_path,
        input_sheet_name=sheet_name,
    )
