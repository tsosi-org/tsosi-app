from datetime import date
from pathlib import Path

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_DAY, DATE_PRECISION_YEAR


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="doab_oapen",
        entity_id="doab_oapen",
        full_data=True,
        data_load_name=Path(file_path).name,
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "doab_oapen",
        ".xlsx",
        source,
        input_file_name=file_path,
        input_sheet_name=sheet_name,
        fields=[
            rdc.FieldEmitterName(field="emitter/name"),
            rdc.FieldEmitterCountry(field="emitter/country"),
            rdc.FieldEmitterRorId(field="emitter/ror_id"),
            rdc.FieldEmitterWikidataId(field="emitter/wikidata_id"),
            rdc.FieldAgentName(field="intermediary/name"),
            rdc.FieldAgentRorId(field="intermediary/ror_id"),
            rdc.FieldAgentWikidataId(field="intermediary/wikidata_id"),
            rdc.FieldRecipientName(constant="OAPEN & DOAB"),
            rdc.FieldRecipientCustomId(constant="doab_oapen"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldCurrency(field="currency"),
            rdc.FieldHideAmount(constant=True),
            rdc.FieldDateStart(field="support_start_date"),
            rdc.FieldDateEnd(field="support_end_date"),
        ],
    )
