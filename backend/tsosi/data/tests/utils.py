from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Type
from urllib.parse import unquote_plus

import pytest


@dataclass
class BaseTestData:
    args: Iterable[Any] = field(default=list)  # type:ignore
    kwargs: dict[str, Any] = field(default_factory=dict)
    result: Any | None = None
    # Callable that must evaluate to True if the result is the expected one
    test_result: Callable | None = None
    exception: Type[Exception] | None = None


def base_test_function(func: Callable, test_data: Iterable[BaseTestData]):
    """
    Test a simple function iteratively with the provided test data.
    Cf. `TestData` dataclass.
    """
    for test in test_data:
        if test.exception is not None:
            with pytest.raises(test.exception):
                func(*test.args, **test.kwargs)
            continue
        result = func(*test.args, **test.kwargs)
        if test.test_result is not None:
            assert test.test_result(result)
        else:
            assert result == test.result or (
                result is None and test.result is None
            ), f"Expected {test.result}, got {result}"


class MockAiohttpResponse:
    def __init__(
        self,
        status=200,
        text: str | None = None,
        json: dict | list | None = None,
        content: bytes | None = None,
        url: str | None = None,
    ):
        self.status = status
        self._text = text
        self._json = json
        self._content = content
        self.url = unquote_plus(url) if url else "http://localhost/api/test/"

    async def text(self):
        return self._text

    async def json(self):
        return self._json

    async def read(self):
        return self._content

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self
