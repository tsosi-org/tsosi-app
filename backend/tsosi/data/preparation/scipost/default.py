from datetime import date

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_DAY


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="scipost",
        full_data=True,
        data_load_name=file_path.split("/")[-1],
        date_data_obtained=date_data,
    )
    return rdc.RawDataConfigFromFile(
        "scipost_api",
        ".xlsx",
        source,
        fields=[
            rdc.FieldRecipientName(constant="SciPost"),
            rdc.FieldRecipientWikidataId(constant="Q52663237"),
            rdc.FieldEmitterName(field="emitter_name"),
            rdc.FieldEmitterCountry(field="emitter_country", is_iso=True),
            rdc.FieldEmitterRorId(field="emitter_ror_id"),
            rdc.FieldEmitterWikidataId(field="emitter_wikidata_id"),
            rdc.FieldEmitterUrl(field="emitter_website"),
            rdc.FieldEmitterType(field="emitter_type"),
            rdc.FieldAmount(field="amount"),
            rdc.FieldHideAmount(field="hide_amount"),
            rdc.FieldCurrency(constant="EUR"),
            rdc.FieldDatePayment(field="payment_date"),
            rdc.FieldDateInvoice(field="invoice_date"),
            rdc.FieldDateStart(
                field="subsidy_date_from",
                format="%Y-%m-%d",
                date_precision=DATE_PRECISION_DAY,
            ),
            rdc.FieldDateEnd(
                field="subsidy_date_until",
                format="%Y-%m-%d",
                date_precision=DATE_PRECISION_DAY,
            ),
        ],
        input_file_name=file_path,
        input_sheet_name=sheet_name,
    )
