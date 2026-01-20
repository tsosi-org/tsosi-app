from datetime import date

from tsosi.data.preparation import raw_data_config as rdc
from tsosi.models.date import DATE_PRECISION_YEAR, Date


def get_config(
    file_path: str, sheet_name: str, date_data: date
) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="doaj_library",
        year=2023,
        full_data=True,
        data_load_name=file_path.split("/")[-1],
        date_data_obtained=date_data,
        entity_id="05amyt365",
    )
    return rdc.RawDataConfigFromFile(
        "doaj_library_2023",
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
            rdc.FieldAgentName(field="agent/consortium"),
            rdc.FieldAgentUrl(field="agent_website"),
            rdc.FieldAgentWikidataId(field="agent_wikidata_id"),
            rdc.FieldAgentRorId(field="agent_ror_id"),
            rdc.FieldDatePaymentRecipient(
                field="date_payment_recipient",
                format="%Y-%m-%d",
                date_precision=DATE_PRECISION_YEAR,
                default=Date(
                    value=date(year=2023, month=1, day=1),
                    precision=DATE_PRECISION_YEAR,
                ).serialize(),
            ),
            rdc.FieldDatePaymentEmitter(
                field="date_payment_emitter", date_precision=DATE_PRECISION_YEAR
            ),
        ],
        date_columns=["date_payment_recipient", "date_payment_emitter"],
        input_file_name=file_path,
        input_sheet_name=sheet_name,
    )
