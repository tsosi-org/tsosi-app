from datetime import date
from pathlib import Path

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_DAY, DATE_PRECISION_YEAR


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="mdc",
        entity_id="Q139497168",
        full_data=True,
        data_load_name=Path(file_path).name,
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "mdc",
        ".xlsx",
        source,
        input_file_name=file_path,
        input_sheet_name=sheet_name,
        fields=[
            rdc.FieldEmitterName(field="emitter/name"),
            rdc.FieldEmitterRorId(field="emitter/ror_id"),
            rdc.FieldEmitterCountry(field="emitter/country"),
            rdc.FieldAgentName(field="agent/name"),
            rdc.FieldAgentRorId(field="agent/ror_id"),
            rdc.FieldRecipientName(constant="Make Data Count"),
            rdc.FieldRecipientWikidataId(constant="Q139497168"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldCurrency(constant="EUR"),
            rdc.FieldHideAmount(constant=False),
            rdc.FieldDatePaymentRecipient(field="date_received"),
        ],
    )
