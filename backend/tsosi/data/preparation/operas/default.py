from datetime import date

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_YEAR


def get_config(
    file_path: str, sheet_name: str, year: int, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="operas",
        year=year,
        full_data=True,
        data_load_name=file_path.split("/")[-1],
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "operas",
        ".xlsx",
        source,
        fields=[
            rdc.FieldRecipientName(constant="OPERAS"),
            rdc.FieldRecipientRorId(constant="00rfexj26"),
            rdc.FieldEmitterName(field="Emitter"),
            rdc.FieldEmitterCountry(field="Country"),
            rdc.FieldEmitterRorId(field="emitter_ror_id"),
            rdc.FieldEmitterWikidataId(field="emitter_wikidata_id"),
            rdc.FieldEmitterType(field="Category"),
            rdc.FieldAmount(field="Value"),
            rdc.FieldHideAmount(constant=False),
            rdc.FieldCurrency(field="Currency"),
            rdc.FieldDatePaymentRecipient(
                field="Date", format="%Y", date_precision=DATE_PRECISION_YEAR
            ),
        ],
        input_file_name=file_path,
        input_sheet_name=sheet_name,
    )
