from datetime import date

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_DAY, DATE_PRECISION_YEAR, Date


def get_config(
    year: int, file_path: str, sheet_name: str
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="doaj_library",
        year=year,
        full_data=True,
        data_load_name=file_path.split("/")[-1],
    )
    return rdc.RawDataConfigFromFile(
        "doaj_library_2024+",
        ".xlsx",
        source,
        fields=[
            rdc.FieldRecipientName(
                constant="Directory of Open Access Journals"
            ),
            rdc.FieldRecipientRorId(constant="05amyt365"),
            rdc.FieldEmitterName(field="Company"),
            rdc.FieldEmitterCountry(field="Country", is_iso=False),
            rdc.FieldAmount(field="Support amount"),
            rdc.FieldCurrency(field="Currency"),
            rdc.FieldConsortiumName(field="Agent"),
            rdc.FieldDateInvoice(
                field="Invoice date",
                format="%d/%m/%Y",
                default=Date(
                    value=date(year=2024, month=1, day=1),
                    precision=DATE_PRECISION_YEAR,
                ).serialize(),
                date_precision=DATE_PRECISION_DAY,
            ),
        ],
        date_columns=["Invoice date", "Support end date", "Paid up until"],
        input_file_name=file_path,
        input_sheet_name=sheet_name,
        hide_amount=True,
    )
