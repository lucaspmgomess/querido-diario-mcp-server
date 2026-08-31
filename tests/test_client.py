"""Tests for `QueridoDiarioClient`.

All requests go through `httpx.MockTransport`, so nothing here touches the network.
"""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from querido_diario_mcp_server.client import QueridoDiarioClient
from querido_diario_mcp_server.config import ClientConfig
from querido_diario_mcp_server.errors import (
    QDBadRequestError,
    QDConnectionError,
    QDNotFoundError,
    QDResponseParsingError,
    QDServerError,
    QDTimeoutError,
)
from querido_diario_mcp_server.models import SortBy

BASE_URL = "https://qd-test.invalid"


def make_client(handler: Callable[[httpx.Request], httpx.Response]) -> QueridoDiarioClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(base_url=BASE_URL, transport=transport)
    return QueridoDiarioClient(config=ClientConfig(base_url=BASE_URL), http_client=http_client)


def json_response(status_code: int, payload: object) -> httpx.Response:
    return httpx.Response(status_code, json=payload)


CITY_RECIFE = {
    "territory_id": "2611606",
    "territory_name": "Recife",
    "state_code": "PE",
    "publication_urls": ["https://example.org/recife"],
    "level": "1",
    "availability_date": "2019-06-01",
}

CITY_RECIFE_MINAS = {
    "territory_id": "3155306",
    "territory_name": "Recife",
    "state_code": "MG",
    "level": "1",
    "availability_date": "2020-01-01",
}


GAZETTE_ITEM = {
    "territory_id": "2611606",
    "territory_name": "Recife",
    "state_code": "PE",
    "date": "2026-03-10",
    "scraped_at": "2026-03-11T08:00:00",
    "url": "https://example.org/gazette.pdf",
    "excerpts": ["...trecho encontrado..."],
    "edition": "123",
    "is_extra_edition": False,
    "txt_url": "https://example.org/gazette.txt",
}


class TestSearchCities:
    @pytest.mark.asyncio
    async def test_returns_parsed_cities(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/cities"
            assert request.url.params["city_name"] == "Recife"
            return json_response(200, {"cities": [CITY_RECIFE]})

        client = make_client(handler)
        result = await client.search_cities("Recife")

        assert len(result.cities) == 1
        assert result.cities[0].territory_id == "2611606"
        assert result.cities[0].state_code == "PE"

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return json_response(200, {"cities": []})

        client = make_client(handler)
        result = await client.search_cities("Cidade Que Nao Existe")

        assert result.cities == []

    @pytest.mark.asyncio
    async def test_multiple_same_name_different_states(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return json_response(200, {"cities": [CITY_RECIFE, CITY_RECIFE_MINAS]})

        client = make_client(handler)
        result = await client.search_cities("Recife")

        assert {c.state_code for c in result.cities} == {"PE", "MG"}


class TestGetCity:
    @pytest.mark.asyncio
    async def test_returns_parsed_city(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/cities/2611606"
            return json_response(200, {"city": CITY_RECIFE})

        client = make_client(handler)
        city = await client.get_city("2611606")

        assert city.territory_name == "Recife"
        assert city.availability_date == "2019-06-01"

    @pytest.mark.asyncio
    async def test_upstream_404_raises_not_found(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return json_response(404, {"detail": "City not found."})

        client = make_client(handler)
        with pytest.raises(QDNotFoundError) as exc_info:
            await client.get_city("0000000")

        assert exc_info.value.status_code == 404


class TestSearchGazettes:
    @pytest.mark.asyncio
    async def test_returns_parsed_gazettes(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/gazettes"
            return json_response(200, {"total_gazettes": 1, "gazettes": [GAZETTE_ITEM]})

        client = make_client(handler)
        result = await client.search_gazettes(querystring="licitação")

        assert result.total_gazettes == 1
        assert result.gazettes[0].territory_id == "2611606"
        assert result.gazettes[0].excerpts == ["...trecho encontrado..."]

    @pytest.mark.asyncio
    async def test_preserves_exact_query_string(self) -> None:
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["querystring"] = request.url.params["querystring"]
            return json_response(200, {"total_gazettes": 0, "gazettes": []})

        client = make_client(handler)
        await client.search_gazettes(querystring='"João da Silva"')

        assert captured["querystring"] == '"João da Silva"'

    @pytest.mark.asyncio
    async def test_serializes_multiple_territory_ids(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.params.get_list("territory_ids") == ["2611606", "3550308"]
            return json_response(200, {"total_gazettes": 0, "gazettes": []})

        client = make_client(handler)
        await client.search_gazettes(territory_ids=["2611606", "3550308"])

    @pytest.mark.asyncio
    async def test_omits_territory_ids_when_not_given(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert "territory_ids" not in request.url.params
            return json_response(200, {"total_gazettes": 0, "gazettes": []})

        client = make_client(handler)
        await client.search_gazettes()

    @pytest.mark.asyncio
    async def test_date_range_params(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.params["published_since"] == "2026-01-01"
            assert request.url.params["published_until"] == "2026-07-31"
            return json_response(200, {"total_gazettes": 0, "gazettes": []})

        client = make_client(handler)
        await client.search_gazettes(published_since="2026-01-01", published_until="2026-07-31")

    @pytest.mark.asyncio
    async def test_pagination_params(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.params["size"] == "20"
            assert request.url.params["offset"] == "40"
            return json_response(200, {"total_gazettes": 0, "gazettes": []})

        client = make_client(handler)
        await client.search_gazettes(size=20, offset=40)

    @pytest.mark.asyncio
    async def test_sort_by_param(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.params["sort_by"] == "ascending_date"
            return json_response(200, {"total_gazettes": 0, "gazettes": []})

        client = make_client(handler)
        await client.search_gazettes(sort_by=SortBy.ASCENDING_DATE)

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return json_response(200, {"total_gazettes": 0, "gazettes": []})

        client = make_client(handler)
        result = await client.search_gazettes(querystring="termo inexistente")

        assert result.total_gazettes == 0
        assert result.gazettes == []


class TestErrorMapping:
    @pytest.mark.asyncio
    async def test_upstream_400_raises_bad_request(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return json_response(400, {"detail": "Invalid CNPJ"})

        client = make_client(handler)
        with pytest.raises(QDBadRequestError) as exc_info:
            await client.search_gazettes()

        assert exc_info.value.status_code == 400
        assert "Invalid CNPJ" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upstream_422_raises_bad_request(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return json_response(422, {"detail": [{"msg": "invalid date"}]})

        client = make_client(handler)
        with pytest.raises(QDBadRequestError) as exc_info:
            await client.search_gazettes()

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_upstream_500_raises_server_error(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        client = make_client(handler)
        with pytest.raises(QDServerError) as exc_info:
            await client.search_gazettes()

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_upstream_503_raises_server_error(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="Service Unavailable")

        client = make_client(handler)
        with pytest.raises(QDServerError) as exc_info:
            await client.search_cities("qualquer")

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_malformed_json_raises_parsing_error(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html>not json</html>", headers={"content-type": "text/html"})

        client = make_client(handler)
        with pytest.raises(QDResponseParsingError):
            await client.search_cities("qualquer")

    @pytest.mark.asyncio
    async def test_unexpected_json_shape_raises_parsing_error(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return json_response(200, {"unexpected": "shape"})

        client = make_client(handler)
        with pytest.raises(QDResponseParsingError):
            await client.search_cities("qualquer")

    @pytest.mark.asyncio
    async def test_unexpected_get_city_shape_raises_parsing_error(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return json_response(200, {"unexpected": "shape"})

        client = make_client(handler)
        with pytest.raises(QDResponseParsingError):
            await client.get_city("2611606")

    @pytest.mark.asyncio
    async def test_unexpected_gazettes_shape_raises_parsing_error(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return json_response(200, {"unexpected": "shape"})

        client = make_client(handler)
        with pytest.raises(QDResponseParsingError):
            await client.search_gazettes()

    @pytest.mark.asyncio
    async def test_non_json_error_body_detail(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(400, text="plain text error", headers={"content-type": "text/plain"})

        client = make_client(handler)
        with pytest.raises(QDBadRequestError) as exc_info:
            await client.search_gazettes()

        assert "non-JSON error response" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_body_without_detail_key(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return json_response(400, ["some", "list", "shaped", "error"])

        client = make_client(handler)
        with pytest.raises(QDBadRequestError) as exc_info:
            await client.search_gazettes()

        assert "some" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_body_html_is_not_leaked_verbatim(self) -> None:
        huge_html = "<html>" + ("x" * 5000) + "</html>"

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(502, text=huge_html, headers={"content-type": "text/html"})

        client = make_client(handler)
        with pytest.raises(QDServerError) as exc_info:
            await client.search_cities("qualquer")

        assert huge_html not in str(exc_info.value)
        assert len(str(exc_info.value)) < 1000

    @pytest.mark.asyncio
    async def test_timeout_raises_qd_timeout_error(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        client = make_client(handler)
        with pytest.raises(QDTimeoutError):
            await client.search_cities("qualquer")

    @pytest.mark.asyncio
    async def test_connection_error_raises_qd_connection_error(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        client = make_client(handler)
        with pytest.raises(QDConnectionError):
            await client.search_cities("qualquer")


class TestClientLifecycle:
    @pytest.mark.asyncio
    async def test_does_not_close_externally_supplied_http_client(self) -> None:
        transport = httpx.MockTransport(lambda r: json_response(200, {"cities": []}))
        http_client = httpx.AsyncClient(base_url=BASE_URL, transport=transport)
        client = QueridoDiarioClient(config=ClientConfig(base_url=BASE_URL), http_client=http_client)

        await client.search_cities("qualquer")
        await client.aclose()

        assert not http_client.is_closed

        await http_client.aclose()

    @pytest.mark.asyncio
    async def test_context_manager_closes_owned_client(self) -> None:
        config = ClientConfig(base_url=BASE_URL)
        async with QueridoDiarioClient(config=config) as client:
            assert not client.is_closed
        assert client.is_closed
