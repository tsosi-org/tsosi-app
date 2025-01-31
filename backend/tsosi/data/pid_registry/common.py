import asyncio
from dataclasses import dataclass
from typing import Callable, Sequence

import aiohttp
import pandas as pd

TSOSI_USER_AGENT = "TSOSI-python-bot/0.1 (contact@tsosi.org)"


class HTTPStatusError(Exception):
    pass


@dataclass(kw_only=True)
class ApiResult:
    error: bool = False
    error_message: str | None = None


async def perform_http_func_batch[
    T, P
](
    data: Sequence[T],
    func: Callable[[aiohttp.ClientSession, T], P],
    max_conns: int = 30,
) -> list[P]:
    """
    Call the given function performing HTTP calls for every data items in
    an async client session.

    :param data:        The sequence of items for which `func` must be
                        applied.
    :param func:        The function to be applied for every data item.
                        It must take as arguments an `aiohttp.ClientSession`
                        and a data item.
    :param max_conns:   The maximum number of simultaneously opened
                        HTTP connections.
    :returns:           The results of the `func` call for every item.
    """
    headers = {"User-Agent": TSOSI_USER_AGENT}
    timeout = aiohttp.ClientTimeout(sock_connect=5)
    # Limit the number of simultaneously opened connections
    conn = aiohttp.TCPConnector(limit=max_conns)
    async with aiohttp.ClientSession(
        connector=conn, timeout=timeout, headers=headers
    ) as session:
        tasks = [func(session, item) for item in data]
        results = await asyncio.gather(*tasks)

    return results
