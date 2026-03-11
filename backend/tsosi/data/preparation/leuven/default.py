from datetime import date
from pathlib import Path

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_DAY, DATE_PRECISION_YEAR


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="leuven",
        entity_id="05f950310",
        full_data=True,
        data_load_name=Path(file_path).name,
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "leuven",
        ".xlsx",
        source,
        input_file_name=file_path,
        input_sheet_name=sheet_name,
        fields=[
            rdc.FieldEmitterName(constant="KU Leuven"),
            rdc.FieldEmitterRorId(constant="05f950310"),
            rdc.FieldAgentName(field="intermediary/name"),
            rdc.FieldAgentRorId(field="intermediary/ror_id"),
            rdc.FieldAgentWikidataId(field="intermediary/wikidata_id"),
            rdc.FieldRecipientName(field="recipient/name"),
            rdc.FieldRecipientRorId(field="recipient/ror_id"),
            rdc.FieldRecipientWikidataId(field="recipient/wikidata_id"),
            rdc.FieldRecipientCustomId(field="recipient/custom_id"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldCurrency(field="currency"),
            rdc.FieldHideAmount(field="hide_amount"),
            rdc.FieldDatePaymentEmitter(field="date_invoice"),
            rdc.FieldDateStart(field="contract/date_start"),
            rdc.FieldDateEnd(field="contract/date_end"),
        ],
    )
