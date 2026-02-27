from datetime import date
from pathlib import Path

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_DAY, DATE_PRECISION_YEAR


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="liege",
        entity_id="00afp2z80",
        full_data=True,
        data_load_name=Path(file_path).name,
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "liege",
        ".xlsx",
        source,
        input_file_name=file_path,
        input_sheet_name=sheet_name,
        fields=[
            rdc.FieldEmitterName(constant="University of Liège"),
            rdc.FieldEmitterRorId(constant="00afp2z80"),
            rdc.FieldRecipientName(field="recipient/name"),
            rdc.FieldRecipientRorId(field="recipient/ror_id"),
            rdc.FieldRecipientWikidataId(field="recipient/wikidata_id"),
            rdc.FieldAgentName(field="intermediary/name"),
            rdc.FieldAgentRorId(field="intermediary/ror_id"),
            rdc.FieldAgentWikidataId(field="intermediary/wikidata_id"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldHideAmount(constant=False),
            rdc.FieldCurrency(constant="EUR"),
            rdc.FieldDatePaymentRecipient(field="date_received"),
        ],
    )
