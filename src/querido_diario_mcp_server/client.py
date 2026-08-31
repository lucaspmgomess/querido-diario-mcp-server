"""Asynchronous HTTP client for the public Querido Diário API.

This module knows nothing about the Model Context Protocol. It is a small, typed,
testable wrapper around the upstream FastAPI service documented at
https://docs.queridodiario.ok.org.br/en/latest/using/public-api.html and implemented
at https://github.com/okfn-brasil/querido-diario-api.

Only the read-only endpoints this project exposes as MCP tools are implemented:
`GET /cities`, `GET /cities/{territory_id}`, and `GET /gazettes`.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self, cast

import httpx
from pydantic import ValidationError

from querido_diario_mcp_server.config import ClientConfig, load_config
from querido_diario_mcp_server.errors import (
    QDBadRequestError,
    QDConnectionError,
    QDError,
    QDNotFoundError,
    QDResponseParsingError,
    QDServerError,
    QDTimeoutError,
)
from querido_diario_mcp_server.models import (
    CitiesResponse,
    City,
    CityResponse,
    GazetteSearchResponse,
    SortBy,
)

_MAX_ERROR_DETAIL_LEN = 300


def _extract_detail(response: httpx.Response) -> str:
    """Pull a short, safe error message out of an upstream error response.

    Never returns the raw response body verbatim: a non-JSON body (e.g. an HTML
    error page from a proxy) is replaced with a generic note instead of being
    forwarded to the caller.
    """
    try:
        data: Any = response.json()
    except ValueError:
        return f"non-JSON error response (content-type: {response.headers.get('content-type', 'unknown')})"
    detail: Any = data
    if isinstance(data, dict):
        # response.json() is untyped JSON; a dict key is always str, so this narrowing is safe.
        payload = cast(dict[str, Any], data)
        if "detail" in payload:
            detail = payload["detail"]
    return str(detail)[:_MAX_ERROR_DETAIL_LEN]


class QueridoDiarioClient:
    """Async client for the Querido Diário public API.

    Reuses a single `httpx.AsyncClient` connection pool across calls. Instantiate it
    once (ideally as part of an application/server lifespan) and call `aclose()` when
    done, or use it as an async context manager.

    A custom `http_client` can be supplied for testing (e.g. one built with
    `httpx.MockTransport`); in that case this class does not own it and will not
    close it.
    """

    def __init__(
        self,
        config: ClientConfig | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config or load_config()
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=httpx.Timeout(
                connect=self._config.connect_timeout,
                read=self._config.read_timeout,
                write=self._config.write_timeout,
                pool=self._config.pool_timeout,
            ),
            headers={"User-Agent": self._config.user_agent},
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool, if this client owns it."""
        if self._owns_client:
            await self._client.aclose()

    @property
    def is_closed(self) -> bool:
        """Whether the underlying HTTP connection pool has been closed."""
        return self._client.is_closed

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        try:
            response = await self._client.get(path, params=params)
        except httpx.TimeoutException as exc:
            raise QDTimeoutError(f"Timed out while requesting {path}") from exc
        except httpx.ConnectError as exc:
            raise QDConnectionError(
                f"Could not connect to the Querido Diário API at {self._config.base_url}"
            ) from exc
        except httpx.HTTPError as exc:
            raise QDConnectionError(f"Network error while requesting {path}: {exc}") from exc

        if response.status_code == 404:
            raise QDNotFoundError(f"Resource not found: {path}", status_code=404)
        if response.status_code in (400, 422):
            raise QDBadRequestError(
                f"Querido Diário API rejected the request to {path}: {_extract_detail(response)}",
                status_code=response.status_code,
            )
        if response.status_code >= 500:
            raise QDServerError(
                f"Querido Diário API returned a server error ({response.status_code}) for {path}",
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            raise QDError(
                f"Unexpected HTTP {response.status_code} from {path}: {_extract_detail(response)}",
                status_code=response.status_code,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise QDResponseParsingError(
                f"Could not parse the response from {path} as JSON "
                f"(content-type: {response.headers.get('content-type', 'unknown')})"
            ) from exc

    async def search_cities(self, city_name: str = "") -> CitiesResponse:
        """Search municipalities by (partial) name via `GET /cities`."""
        data = await self._get("/cities", {"city_name": city_name})
        try:
            return CitiesResponse.model_validate(data)
        except ValidationError as exc:
            raise QDResponseParsingError("Unexpected response shape from GET /cities") from exc

    async def get_city(self, territory_id: str) -> City:
        """Fetch a single municipality by its 7-digit IBGE ID via `GET /cities/{id}`."""
        data = await self._get(f"/cities/{territory_id}", {})
        try:
            return CityResponse.model_validate(data).city
        except ValidationError as exc:
            raise QDResponseParsingError(
                f"Unexpected response shape from GET /cities/{territory_id}"
            ) from exc

    async def search_gazettes(
        self,
        *,
        querystring: str = "",
        territory_ids: list[str] | None = None,
        published_since: str | None = None,
        published_until: str | None = None,
        size: int = 10,
        offset: int = 0,
        sort_by: SortBy = SortBy.RELEVANCE,
        excerpt_size: int = 500,
        number_of_excerpts: int = 1,
    ) -> GazetteSearchResponse:
        """Search gazette content via `GET /gazettes`.

        `published_since` / `published_until` are ISO `YYYY-MM-DD` date strings.
        `querystring` uses OpenSearch's simple query string syntax upstream.
        """
        params: dict[str, Any] = {
            "querystring": querystring,
            "size": size,
            "offset": offset,
            "sort_by": sort_by.value,
            "excerpt_size": excerpt_size,
            "number_of_excerpts": number_of_excerpts,
        }
        if territory_ids:
            params["territory_ids"] = territory_ids
        if published_since:
            params["published_since"] = published_since
        if published_until:
            params["published_until"] = published_until

        data = await self._get("/gazettes", params)
        try:
            return GazetteSearchResponse.model_validate(data)
        except ValidationError as exc:
            raise QDResponseParsingError("Unexpected response shape from GET /gazettes") from exc
