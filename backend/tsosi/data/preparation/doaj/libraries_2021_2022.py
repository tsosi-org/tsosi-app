from datetime import date

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_YEAR, Date


def get_config(
    year: int, file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="doaj_library",
        year=year,
        full_data=True,
        data_load_name=file_path.split("/")[-1],
        date_data_obtained=date_data,
        entity_id="05amyt365",
    )
    return rdc.RawDataConfigFromFile(
        "doaj_library_2021_2022",
        ".xlsx",
        source,
        fields=[
            rdc.FieldRecipientName(
                constant="Directory of Open Access Journals"
            ),
            rdc.FieldRecipientRorId(constant="05amyt365"),
            rdc.FieldEmitterName(field="Institution name"),
            rdc.FieldEmitterUrl(field="emitter_website"),
            rdc.FieldEmitterWikidataId(field="emitter_wikidata_id"),
            rdc.FieldEmitterRorId(field="emitter_ror_id"),
            rdc.FieldEmitterCountry(field="country", is_iso=False),
            rdc.FieldAmount(field="amount"),
            rdc.FieldHideAmount(constant=True),
            rdc.FieldCurrency(field="currency"),
            rdc.FieldDatePaymentRecipient(
                constant=Date(
                    value=date(year=year, month=1, day=1),
                    precision=DATE_PRECISION_YEAR,
                ).serialize()
            ),
        ],
        input_file_name=file_path,
        input_sheet_name=sheet_name,
    )
