from datetime import date, datetime

import pandas as pd
from tsosi.data.data_preparation import (
    clean_cell_value,
    clean_number_value,
    clean_url,
    country_check_iso,
    country_iso_from_name,
    country_name_from_iso,
    currency_iso_from_value,
    extract_currency_amount,
    undate,
)
from tsosi.data.exceptions import DataValidationError

from .utils import BaseTestData, base_test_function


def test_currency_iso_from_value():
    test_data = [
        BaseTestData(args=["USD"], result="USD"),
        BaseTestData(args=["USDs"], result="USD"),
        BaseTestData(args=["USD ($)"], result="USD"),
        BaseTestData(args=["($) USD"], result="USD"),
        BaseTestData(args=["anything $"], result="USD"),
        BaseTestData(args=["anythingOJs €"], result="EUR"),
        BaseTestData(args=["TestMore £ azoi"], result="GBP"),
        BaseTestData(args=["USDPOI"], result="USD"),
        BaseTestData(args=[None], result=None),
        BaseTestData(args=[12], result=None),
        BaseTestData(args=["UUU"], result=None),
        BaseTestData(
            args=["UUU"], kwargs={"error": True}, exception=DataValidationError
        ),
    ]
    base_test_function(currency_iso_from_value, test_data)


def test_country_check_iso():
    test_data = [
        BaseTestData(args=["FR"]),
        BaseTestData(args=["US"]),
        BaseTestData(args=["DK"]),
        BaseTestData(args=["USA"]),
        BaseTestData(
            args=["USA"], kwargs={"error": True}, exception=DataValidationError
        ),
    ]
    base_test_function(country_check_iso, test_data)


def test_country_iso_from_name():
    test_data = [
        BaseTestData(args=["France"], result="FR"),
        BaseTestData(args=["USA"], result="US"),
        BaseTestData(args=["Russia"], result="RU"),
        BaseTestData(args=["Canada"], result="CA"),
        BaseTestData(args=["FR"], result=None),
        BaseTestData(args=[102], result=None),
        BaseTestData(
            args=["FR"], kwargs={"error": True}, exception=DataValidationError
        ),
        BaseTestData(
            args=[102], kwargs={"error": True}, exception=DataValidationError
        ),
    ]
    base_test_function(country_iso_from_name, test_data)


def test_country_name_from_iso():
    test_data = [
        BaseTestData(args=["FR"], result="France"),
        BaseTestData(args=["France"], result="France"),
    ]
    base_test_function(country_name_from_iso, test_data)


def test_clean_url():
    test_data = [
        BaseTestData(args=["https://myurl.org/"], result="https://myurl.org"),
        BaseTestData(args=["https://myurl.org"], result="https://myurl.org"),
        BaseTestData(args=["http://myurl.org/"], result="http://myurl.org"),
        BaseTestData(args=["myurl.org"], result="https://myurl.org"),
        BaseTestData(args=[None], result=None),
    ]
    base_test_function(clean_url, test_data)


def test_clean_cell_value():
    test_data = [
        BaseTestData(args=["perfect string"], result="perfect string"),
        BaseTestData(
            args=[
                """
                       so many  
                       spaces   everywhere
                       """
            ],
            result="so many spaces everywhere",
        ),
        BaseTestData(args=[None], result=None),
        BaseTestData(args=[102], result=102),
    ]
    base_test_function(clean_cell_value, test_data)


def test_clean_number_value():
    test_data = [
        BaseTestData(args=["1.245"], result=1.245),
        BaseTestData(args=["1,245"], result=1245),
        BaseTestData(args=["1 245"], result=1245),
        BaseTestData(
            args=["1,245"], kwargs={"comma_decimal": True}, result=1.245
        ),
        BaseTestData(args=[None], result=None),
        BaseTestData(args=["azaze"], test_result=pd.isna),
    ]
    base_test_function(clean_number_value, test_data)


def test_extract_currency_amount():
    test_data = [
        BaseTestData(args=["1200"], result=("1200", None)),
        BaseTestData(args=["1200 €"], result=("1200", "€")),
        BaseTestData(args=["$1200"], result=("1200", "$")),
        BaseTestData(args=["$ 1,200"], result=("1,200", "$")),
        BaseTestData(args=["$ 1.200"], result=("1.200", "$")),
        BaseTestData(args=["CAD $ 1 200"], result=("1200", "CAD $")),
        BaseTestData(args=["wrong data"], result=(None, None)),
        BaseTestData(
            args=["wrong data"],
            kwargs={"error": True},
            exception=DataValidationError,
        ),
    ]
    base_test_function(extract_currency_amount, test_data)


def test_undate():
    test_data = [
        BaseTestData(
            args=[datetime(2021, 1, 3)],
            result="2021-01-03",
        ),
        BaseTestData(
            args=[datetime(2021, 1, 3)],
            kwargs={"date_format": "%Y-%m-%d"},
            result="2021-01-03",
        ),
        BaseTestData(
            args=[date(2021, 1, 3)],
            kwargs={"date_format": "%Y-%m-%d"},
            result="2021-01-03",
        ),
        BaseTestData(
            args=[datetime(2021, 1, 3)],
            kwargs={"date_format": "%d/%m/%Y"},
            result="03/01/2021",
        ),
        BaseTestData(args=[None], result=None),
        BaseTestData(args=["2021-01-03"], result="2021-01-03"),
    ]
    base_test_function(undate, test_data)
