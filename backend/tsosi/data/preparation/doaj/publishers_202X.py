from datetime import date

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_YEAR, Date


def get_config(
    year: int, file_path: str, sheet_name: str
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="doaj_publisher",
        year=year,
        full_data=True,
        data_load_name=file_path.split("/")[-1],
    )
    return rdc.RawDataConfigFromFile(
        "doaj_publisher",
        ".xlsx",
        source,
        fields=[
            rdc.FieldRecipientName(
                constant="Directory of Open Access Journals"
            ),
            rdc.FieldRecipientRorId(constant="05amyt365"),
            rdc.FieldEmitterName(field="Company"),
            rdc.FieldEmitterUrl(field="emitter_website"),
            rdc.FieldEmitterRorId(field="emitter_ror_id"),
            rdc.FieldEmitterWikidataId(field="emitter_wikidata_id"),
            rdc.FieldEmitterCountry(field="Country"),
            rdc.FieldAmount(field="Amount"),
            rdc.FieldCurrency(field="Currency"),
            rdc.FieldDatePayment(
                constant=Date(
                    value=date(year=year, month=1, day=1),
                    precision=DATE_PRECISION_YEAR,
                ).serialize()
            ),
        ],
        input_file_name=file_path,
        input_sheet_name=sheet_name,
        hide_amount=True,
    )
