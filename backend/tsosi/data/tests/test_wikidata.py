import asyncio

from tsosi.data.pid_registry.wikidata import fetch_wikidata_records_data


def test_fetch_wikidata_records():
    """TODO: Mock the call to Wikidata API."""
    print("Testing fetching of wikidata records")
    # First value does not exist but has correct syntax
    # Second one is UGA
    # Last one should be filtered out by our code and not be queried
    identifiers = ["Q215432154632121", "Q945876", "QINCORRECT_VALUE"]

    res = asyncio.run(fetch_wikidata_records_data(identifiers))
    assert len(res) == 3
    assert res["error"].tolist() == [False, False, True]
    assert all(
        c in res.columns
        for c in [
            "id",
            "info",
            "record",
            "error",
            "error_msg",
            "http_status",
            "timestamp",
        ]
    )
