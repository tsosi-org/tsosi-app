from datetime import date

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_DAY


def get_config(
    file_path: str, sheet_name: str, year: int, full_data: bool, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="doab_oapen_sponsor",
        year=year,
        full_data=full_data,
        data_load_name=file_path.split("/")[-1],
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "doab_oapen_sponsor",
        ".xlsx",
        source,
        fields=[
            rdc.FieldRecipientName(
                constant="Directory of Open Access Books & OAPEN"
            ),
            rdc.FieldRecipientCustomId(constant="doab_oapen"),
            rdc.FieldEmitterName(field="Company"),
            rdc.FieldEmitterUrl(field="emitter_website"),
            rdc.FieldEmitterWikidataId(field="emitter_wikidata_id"),
            rdc.FieldEmitterRorId(field="emitter_ror_id"),
            rdc.FieldEmitterCountry(field="Country", is_iso=False),
            rdc.FieldAmount(field="amount"),
            rdc.FieldHideAmount(constant=True),
            rdc.FieldCurrency(field="currency"),
            rdc.FieldDateStart(
                field="date_start",
                format="%Y-%m-%d",
                date_precision=DATE_PRECISION_DAY,
            ),
            rdc.FieldDateEnd(
                field="date_end",
                format="%Y-%m-%d",
                date_precision=DATE_PRECISION_DAY,
            ),
        ],
        date_columns=["date_start", "date_end"],
        input_file_name=file_path,
        input_sheet_name=sheet_name,
    )
