"""Integration tests for the MCP server: tool discovery, schemas, and invocation.

Uses the MCP SDK's in-process `Client` (`mcp.client.client.Client`) to drive the real
`MCPServer` instance without a subprocess or network port. The upstream HTTP layer is
still mocked via `httpx.MockTransport`, injected by monkeypatching the
`QueridoDiarioClient` constructor that the server's lifespan calls.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager

import httpx
import pytest
from mcp.client.client import Client
from mcp_types import TextContent

import querido_diario_mcp_server.server as server_module
from querido_diario_mcp_server.client import QueridoDiarioClient
from querido_diario_mcp_server.config import ClientConfig

BASE_URL = "https://qd-test.invalid"

EXPECTED_TOOL_NAMES = {"search_cities", "get_city", "search_gazettes"}

CITY_SP = {
    "territory_id": "3550308",
    "territory_name": "São Paulo",
    "state_code": "SP",
    "publication_urls": ["https://example.org/sp"],
    "level": "1",
    "availability_date": "2018-09-01",
}

GAZETTE_ITEM = {
    "territory_id": "3550308",
    "territory_name": "São Paulo",
    "state_code": "SP",
    "date": "2026-02-01",
    "scraped_at": "2026-02-02T09:00:00",
    "url": "https://example.org/gazette.pdf",
    "excerpts": ["...achou aqui..."],
    "edition": "50",
    "is_extra_edition": False,
    "txt_url": "https://example.org/gazette.txt",
}


def _json(status_code: int, payload: object) -> httpx.Response:
    return httpx.Response(status_code, json=payload)


def _text_of(result) -> str:
    parts = [block.text for block in result.content if isinstance(block, TextContent)]
    return "\n".join(parts)


def _empty_gazettes(_: httpx.Request) -> httpx.Response:
    return _json(200, {"total_gazettes": 0, "gazettes": []})


@asynccontextmanager
async def running_client(monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]):
    """Point the server's lifespan at a `QueridoDiarioClient` backed by a mock transport."""

    def fake_client_factory() -> QueridoDiarioClient:
        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(base_url=BASE_URL, transport=transport)
        return QueridoDiarioClient(config=ClientConfig(base_url=BASE_URL), http_client=http_client)

    monkeypatch.setattr(server_module, "QueridoDiarioClient", fake_client_factory)
    async with Client(server_module.mcp) as client:
        yield client


class TestToolDiscovery:
    @pytest.mark.asyncio
    async def test_server_initializes_and_lists_expected_tools(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async with running_client(monkeypatch, lambda r: _json(200, {"cities": []})) as client:
            result = await client.list_tools()

        assert {t.name for t in result.tools} == EXPECTED_TOOL_NAMES

    @pytest.mark.asyncio
    async def test_only_phase_one_tools_exist(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async with running_client(monkeypatch, lambda r: _json(200, {"cities": []})) as client:
            result = await client.list_tools()

        assert len(result.tools) == len(EXPECTED_TOOL_NAMES)

    @pytest.mark.asyncio
    async def test_tool_schemas_declare_expected_parameters(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async with running_client(monkeypatch, lambda r: _json(200, {"cities": []})) as client:
            result = await client.list_tools()

        by_name = {t.name: t for t in result.tools}

        search_cities_props = by_name["search_cities"].input_schema["properties"]
        assert "city_name" in search_cities_props
        assert "state_code" in search_cities_props

        get_city_props = by_name["get_city"].input_schema["properties"]
        assert "territory_id" in get_city_props

        search_gazettes_props = by_name["search_gazettes"].input_schema["properties"]
        expected_params = (
            "query",
            "territory_ids",
            "published_since",
            "published_until",
            "size",
            "offset",
            "sort_by",
        )
        for expected in expected_params:
            assert expected in search_gazettes_props

        for tool in by_name.values():
            assert tool.description
            assert len(tool.description) > 20


class TestSearchCitiesTool:
    @pytest.mark.asyncio
    async def test_invocation_returns_structured_data(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.params["city_name"] == "São Paulo"
            return _json(200, {"cities": [CITY_SP]})

        async with running_client(monkeypatch, handler) as client:
            result = await client.call_tool("search_cities", {"city_name": "São Paulo"})

        assert result.is_error is False
        assert result.structured_content is not None
        assert result.structured_content["cities"][0]["territory_id"] == "3550308"

    @pytest.mark.asyncio
    async def test_rejects_empty_city_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async with running_client(monkeypatch, lambda r: _json(200, {"cities": []})) as client:
            result = await client.call_tool("search_cities", {"city_name": "   "})

        assert result.is_error is True
        assert "empty" in _text_of(result).lower()

    @pytest.mark.asyncio
    async def test_rejects_invalid_state_code(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async with running_client(monkeypatch, lambda r: _json(200, {"cities": []})) as client:
            result = await client.call_tool("search_cities", {"city_name": "Recife", "state_code": "XYZ"})

        assert result.is_error is True
        assert "state code" in _text_of(result).lower()

    @pytest.mark.asyncio
    async def test_state_code_filters_out_other_states(self, monkeypatch: pytest.MonkeyPatch) -> None:
        recife_pe = {**CITY_SP, "territory_id": "2611606", "territory_name": "Recife", "state_code": "PE"}
        recife_mg = {**CITY_SP, "territory_id": "3155306", "territory_name": "Recife", "state_code": "MG"}

        def handler(_: httpx.Request) -> httpx.Response:
            return _json(200, {"cities": [recife_pe, recife_mg]})

        async with running_client(monkeypatch, handler) as client:
            result = await client.call_tool("search_cities", {"city_name": "Recife", "state_code": "pe"})

        assert result.is_error is False
        cities = result.structured_content["cities"]
        assert len(cities) == 1
        assert cities[0]["state_code"] == "PE"

    @pytest.mark.asyncio
    async def test_upstream_server_error_becomes_readable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        async with running_client(monkeypatch, handler) as client:
            result = await client.call_tool("search_cities", {"city_name": "Recife"})

        assert result.is_error is True
        text = _text_of(result)
        assert "Traceback" not in text
        assert "boom" not in text


class TestGetCityTool:
    @pytest.mark.asyncio
    async def test_invocation_returns_structured_data(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/cities/3550308"
            return _json(200, {"city": CITY_SP})

        async with running_client(monkeypatch, handler) as client:
            result = await client.call_tool("get_city", {"territory_id": "3550308"})

        assert result.is_error is False
        assert result.structured_content["territory_name"] == "São Paulo"

    @pytest.mark.asyncio
    async def test_rejects_malformed_territory_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async with running_client(monkeypatch, lambda r: _json(200, {})) as client:
            result = await client.call_tool("get_city", {"territory_id": "123"})

        assert result.is_error is True
        assert "7 digits" in _text_of(result)

    @pytest.mark.asyncio
    async def test_rejects_non_numeric_territory_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async with running_client(monkeypatch, lambda r: _json(200, {})) as client:
            result = await client.call_tool("get_city", {"territory_id": "abcdefg"})

        assert result.is_error is True
        assert "7 digits" in _text_of(result)

    @pytest.mark.asyncio
    async def test_upstream_not_found_becomes_readable_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return _json(404, {"detail": "City not found."})

        async with running_client(monkeypatch, handler) as client:
            result = await client.call_tool("get_city", {"territory_id": "0000000"})

        assert result.is_error is True
        text = _text_of(result)
        assert "0000000" in text
        assert "Traceback" not in text
        assert "<html" not in text.lower()

    @pytest.mark.asyncio
    async def test_upstream_server_error_becomes_readable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="Service Unavailable")

        async with running_client(monkeypatch, handler) as client:
            result = await client.call_tool("get_city", {"territory_id": "3550308"})

        assert result.is_error is True
        assert "Traceback" not in _text_of(result)


class TestSearchGazettesTool:
    @pytest.mark.asyncio
    async def test_invocation_returns_structured_data(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/gazettes"
            return _json(200, {"total_gazettes": 1, "gazettes": [GAZETTE_ITEM]})

        async with running_client(monkeypatch, handler) as client:
            result = await client.call_tool(
                "search_gazettes",
                {"query": "orçamento", "territory_ids": ["3550308"]},
            )

        assert result.is_error is False
        assert result.structured_content["total_gazettes"] == 1
        assert result.structured_content["gazettes"][0]["territory_id"] == "3550308"

    @pytest.mark.asyncio
    async def test_rejects_since_after_until(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async with running_client(monkeypatch, _empty_gazettes) as client:
            result = await client.call_tool(
                "search_gazettes",
                {"published_since": "2026-07-31", "published_until": "2026-01-01"},
            )

        assert result.is_error is True
        assert "published_since" in _text_of(result)

    @pytest.mark.asyncio
    async def test_rejects_negative_offset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async with running_client(monkeypatch, _empty_gazettes) as client:
            result = await client.call_tool("search_gazettes", {"offset": -1})

        assert result.is_error is True
        assert "offset" in _text_of(result)

    @pytest.mark.asyncio
    async def test_rejects_size_above_maximum(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async with running_client(monkeypatch, _empty_gazettes) as client:
            result = await client.call_tool("search_gazettes", {"size": 5000})

        assert result.is_error is True
        assert "size" in _text_of(result)

    @pytest.mark.asyncio
    async def test_rejects_malformed_territory_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async with running_client(monkeypatch, _empty_gazettes) as client:
            result = await client.call_tool("search_gazettes", {"territory_ids": ["not-a-number"]})

        assert result.is_error is True
        assert "7 digits" in _text_of(result)

    @pytest.mark.asyncio
    async def test_rejects_invalid_sort_by(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async with running_client(monkeypatch, _empty_gazettes) as client:
            result = await client.call_tool("search_gazettes", {"sort_by": "newest_first"})

        assert result.is_error is True
        text = _text_of(result)
        assert "Traceback" not in text
        assert "relevance" in text

    @pytest.mark.asyncio
    async def test_rejects_invalid_date_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async with running_client(monkeypatch, _empty_gazettes) as client:
            result = await client.call_tool("search_gazettes", {"published_since": "31/01/2026"})

        assert result.is_error is True
        assert "YYYY-MM-DD" in _text_of(result)

    @pytest.mark.asyncio
    async def test_integration_error_becomes_readable_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="Service Unavailable")

        async with running_client(monkeypatch, handler) as client:
            result = await client.call_tool("search_gazettes", {"query": "algo"})

        assert result.is_error is True
        text = _text_of(result)
        assert "Traceback" not in text
        assert "Service Unavailable" not in text

    @pytest.mark.asyncio
    async def test_empty_results_are_structured_not_prose(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return _json(200, {"total_gazettes": 0, "gazettes": []})

        async with running_client(monkeypatch, handler) as client:
            result = await client.call_tool("search_gazettes", {"query": "termo raro demais"})

        assert result.is_error is False
        assert result.structured_content == {"total_gazettes": 0, "gazettes": []}
