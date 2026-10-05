import re
import unicodedata
from collections.abc import Iterable, Sequence
from typing import Any
from urllib.parse import urlparse

import numpy as np
import pandas as pd


def clean_null_values(df: pd.DataFrame):
    """
    Replace all null values (`numpy.nan`, `pandas.NA` and `pandas.NaT`)
    with `None` python object.
    """
    df.replace(to_replace=[np.nan, pd.NA, pd.NaT], value=None, inplace=True)


def chunk_df(df: pd.DataFrame, size: int):
    """
    Yield slices of the given dataframe of the specified size.
    """
    for pos in range(0, len(df), size):
        yield df.iloc[pos : pos + size].copy()


def chunk_sequence[T](seq: Sequence[T], chunk_size: int):
    """
    Yield slices of the given sequence of the specified size.
    """
    for i in range(0, len(seq), chunk_size):
        yield seq[i : i + chunk_size]


def drop_keys(d: dict[str, Any], patterns: Iterable[str]):
    """
    Drop the dictionnary's keys matching any of the provided regex patterns.
    """
    keys_to_pop = []
    compiled_patterns = [re.compile(p) for p in patterns]
    for key in d:
        if any(p.match(key) for p in compiled_patterns):
            keys_to_pop.append(key)
    for key in keys_to_pop:
        d.pop(key)


def drop_duplicates_keep_index(
    data: pd.DataFrame,
    group_by: str | list[str],
    indexes_column: str,
    dropna=True,
) -> pd.DataFrame:
    """
    Drop duplicates of the given column value, and add a column with the
    list of indexes that held the duplicated value.
    This filters null values on the duplicate column.
    """
    df = data.copy(deep=True)

    duplicates = df.groupby(by=group_by, dropna=dropna).apply(
        lambda group: list(group.index), include_groups=False
    )
    if duplicates.empty:
        return pd.DataFrame()

    duplicates = duplicates.rename(indexes_column)
    df = (
        df.groupby(by=group_by, dropna=dropna, as_index=False)
        .first()
        .merge(duplicates, on=group_by, how="left")
    )
    return df



def normalize_name(name: str | None) -> str:
    """
    Normalize an organization name for comparison: lowercase, without
    accents, parenthesized parts and punctuation.
    """
    if not name:
        return ""
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = re.sub(r"\(.*?\)", " ", name.casefold())
    name = re.sub(r"[^\w+]+", " ", name)
    return " ".join(name.split())


def url_host(url: str | None) -> str | None:
    """
    Return the host of the URL, without the `www.` prefix.
    The scheme is optional.
    """
    if not url:
        return None
    url = url.strip()
    if "://" not in url:
        url = f"https://{url}"
    host = urlparse(url).hostname
    return host.removeprefix("www.") if host else None

SHARED_HOSTS = [
    "doi.org",
    "github.com",
    "gitlab.com",
    "zenodo.org",
    "sites.google.com",
    "wordpress.com",
    "hypotheses.org",
    "medium.com",
]


def same_site(url: str | None, website: str | None) -> bool:
    """
    Whether the URL belongs to the website domain or one of its subdomains.
    """
    host, site = url_host(url), url_host(website)
    if not host or not site:
        return False
    if any(site == h or site.endswith(f".{h}") for h in SHARED_HOSTS):
        return False
    return host == site or host.endswith(f".{site}")
