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
            rdc.FieldEmitterUrl(field="emitter_website"),
            rdc.FieldEmitterWikidataId(field="emitter_wikidata_id"),
            rdc.FieldEmitterRorId(field="emitter_ror_id"),
            rdc.FieldEmitterCountry(field="Country", is_iso=False),
            rdc.FieldAmount(field="Support amount"),
            rdc.FieldHideAmount(constant=True),
            rdc.FieldCurrency(field="Currency"),
            rdc.FieldAgentName(field="Agent"),
            rdc.FieldAgentUrl(field="agent_website"),
            rdc.FieldAgentWikidataId(field="agent_wikidata_id"),
            rdc.FieldAgentRorId(field="agent_ror_id"),
            # Be careful to set the default date to the lowest priority
            # date, so that it is the information used.
            # If we put the default date to the DatePaymentRecipient,
            # this will always be used for the clc date even if there's an input
            # DateInvoice.
            rdc.FieldDatePaymentRecipient(
                field="date_payment_recipient",
                format="%Y-%m-%d",
                date_precision=DATE_PRECISION_YEAR,
            ),
            rdc.FieldDateInvoice(
                field="Invoice date",
                format="%Y-%m-%d",
                default=Date(
                    value=date(year=2024, month=1, day=1),
                    precision=DATE_PRECISION_YEAR,
                ).serialize(),
            ),
        ],
        date_columns=[
            "Invoice date",
            "Support end date",
            "Paid up until",
            "date_payment_recipient",
        ],
        input_file_name=file_path,
        input_sheet_name=sheet_name,
    )
