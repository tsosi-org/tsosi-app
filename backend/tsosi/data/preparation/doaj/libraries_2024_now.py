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
            rdc.FieldEmitterUrl(field="emitter_website"),
            rdc.FieldEmitterWikidataId(field="emitter_wikidata_id"),
            rdc.FieldEmitterRorId(field="emitter_ror_id"),
            rdc.FieldEmitterCountry(field="Country", is_iso=False),
            rdc.FieldAmount(field="Support amount"),
            rdc.FieldCurrency(field="Currency"),
            rdc.FieldAgentName(field="Agent"),
            rdc.FieldAgentUrl(field="agent_website"),
            rdc.FieldAgentWikidataId(field="agent_wikidata_id"),
            rdc.FieldAgentRorId(field="agent_ror_id"),
            rdc.FieldDateInvoice(
                field="Invoice date",
                format="%Y-%m-%d",
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


def get_fixture_config(year: int, file_path: str) -> rdc.RawDataConfigFromFile:
    source = rdc.DataLoadSource(
        data_source_id="doaj_library",
        year=year,
        full_data=True,
        data_load_name=file_path.split("/")[-1],
    )
    return rdc.RawDataConfigFromFile(
        "doaj_library_2024+",
        ".json",
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
            rdc.FieldCurrency(field="Currency"),
            rdc.FieldAgentName(field="Agent"),
            rdc.FieldAgentUrl(field="agent_website"),
            rdc.FieldAgentWikidataId(field="agent_wikidata_id"),
            rdc.FieldAgentRorId(field="agent_ror_id"),
            rdc.FieldDateInvoice(
                field="Invoice date",
                format="%Y-%m-%d",
                default=Date(
                    value=date(year=2024, month=1, day=1),
                    precision=DATE_PRECISION_YEAR,
                ).serialize(),
                date_precision=DATE_PRECISION_DAY,
            ),
        ],
        date_columns=["Invoice date", "Support end date", "Paid up until"],
        input_file_name=file_path,
        hide_amount=True,
    )
