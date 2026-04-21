from datetime import date
from pathlib import Path

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_DAY, DATE_PRECISION_YEAR


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="mersenne",
        full_data=True,
        data_load_name=Path(file_path).name,
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "mersenne",
        ".xlsx",
        source,
        input_file_name=file_path,
        input_sheet_name=sheet_name,
        fields=[
            rdc.FieldEmitterName(field="emitter/name"),
            rdc.FieldEmitterRorId(field="emitter/ror_id"),
            rdc.FieldEmitterWikidataId(field="emitter/wikidata_id"),
            rdc.FieldEmitterSub(field="emitter/sub"),
            rdc.FieldRecipientName(constant="Mersenne"),
            rdc.FieldRecipientWikidataId(constant="Q55606850"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldCurrency(field="currency"),
            rdc.FieldHideAmount(field="hide_amount"),
            rdc.FieldDateInvoice(field="date_invoice"),
        ],
    )
