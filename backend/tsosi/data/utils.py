import re
from typing import Any, Iterable, Sequence

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
    for key in d.keys():
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
