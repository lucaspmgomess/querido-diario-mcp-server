"""MCP protocol boundary: server instance, lifespan, and tool definitions.

This module is the only place that talks to the MCP SDK. It translates between
`QueridoDiarioClient` (the plain HTTP integration) and the Model Context Protocol:
validating tool arguments, mapping `QDError`s to `ToolError`s the calling model can
read and self-correct from, and returning typed structured output.

Only three tools are exposed, deliberately: `search_cities`, `get_city`, and
`search_gazettes`. The server is strictly read-only — it never fetches arbitrary
URLs (including the `url` / `txt_url` fields upstream returns), which would be an
SSRF vector, and it never writes data anywhere.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from typing import Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from querido_diario_mcp_server import __version__
from querido_diario_mcp_server.client import QueridoDiarioClient
from querido_diario_mcp_server.errors import QDError, QDNotFoundError
from querido_diario_mcp_server.models import CitiesResponse, City, GazetteSearchResponse, SortBy

TERRITORY_ID_PATTERN = re.compile(r"^\d{7}$")
STATE_CODE_PATTERN = re.compile(r"^[A-Za-z]{2}$")
MAX_GAZETTE_RESULT_SIZE = 50

INSTRUCTIONS = (
    "Read-only access to the public Querido Diário API, which indexes official "
    "gazettes (diários oficiais) published by Brazilian municipalities. This is an "
    "unofficial, community-built server — it is not affiliated with or endorsed by "
    "Open Knowledge Brasil, the organization behind Querido Diário. To search gazette "
    "content for a named city, first call search_cities to resolve its 7-digit IBGE "
    "territory ID, then pass that ID to search_gazettes."
)


@dataclass
class AppContext:
    """State shared across tool calls for the lifetime of the server process."""

    client: QueridoDiarioClient


@asynccontextmanager
async def app_lifespan(server: MCPServer[AppContext]) -> AsyncIterator[AppContext]:
    client = QueridoDiarioClient()
    try:
        yield AppContext(client=client)
    finally:
        await client.aclose()


mcp = MCPServer(
    "querido-diario",
    title="Querido Diário (unofficial)",
    version=__version__,
    instructions=INSTRUCTIONS,
    lifespan=app_lifespan,
)


def _client(ctx: Context[AppContext, None]) -> QueridoDiarioClient:
    return ctx.request_context.lifespan_context.client


def _require_territory_id(territory_id: str) -> str:
    territory_id = territory_id.strip()
    if not TERRITORY_ID_PATTERN.fullmatch(territory_id):
        raise ToolError(
            f"'{territory_id}' is not a valid IBGE territory ID: it must be exactly "
            "7 digits (e.g. '3550308' for São Paulo)."
        )
    return territory_id


def _parse_date(label: str, value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ToolError(f"'{label}' must be an ISO date in YYYY-MM-DD format, got '{value}'.") from exc


@mcp.tool()
async def search_cities(
    ctx: Context[AppContext, None],
    city_name: str,
    state_code: str | None = None,
) -> CitiesResponse:
    """Find Brazilian municipalities indexed by Querido Diário and resolve their 7-digit IBGE territory IDs.

    Call this FIRST whenever a request names a city but you don't already have its
    numeric territory ID — both `get_city` and `search_gazettes` require that ID, not
    a city name. For example, to answer "find gazettes about ACME in Porto Alegre",
    first call search_cities(city_name="Porto Alegre") to get its territory_id, then
    pass that ID to search_gazettes.

    Matching is by partial, case-insensitive name similarity (as implemented by the
    upstream API), not exact string equality, so it tolerates minor spelling
    variation. `state_code` is an optional two-letter Brazilian state/UF filter
    (e.g. "RS", "SP") applied after the upstream search, useful for disambiguating
    cities that share a name across different states.
    """
    if not city_name.strip():
        raise ToolError("city_name must not be empty.")

    normalized_state: str | None = None
    if state_code is not None and state_code.strip():
        normalized_state = state_code.strip().upper()
        if not STATE_CODE_PATTERN.fullmatch(normalized_state):
            raise ToolError(f"'{state_code}' is not a valid two-letter Brazilian state code (e.g. 'RS').")

    try:
        result = await _client(ctx).search_cities(city_name.strip())
    except QDError as exc:
        raise ToolError(str(exc)) from exc

    if normalized_state:
        result = CitiesResponse(cities=[c for c in result.cities if c.state_code == normalized_state])
    return result


@mcp.tool()
async def get_city(ctx: Context[AppContext, None], territory_id: str) -> City:
    """Retrieve one Brazilian municipality by its 7-digit IBGE territory ID.

    Use this when the exact territory_id is already known (from `search_cities`, or
    supplied directly) and you need that city's details: name, state, Querido Diário
    availability date, and known official publication URLs. If you only have a city
    name, call `search_cities` instead.
    """
    validated_id = _require_territory_id(territory_id)
    try:
        return await _client(ctx).get_city(validated_id)
    except QDNotFoundError as exc:
        raise ToolError(f"No city found with territory_id '{validated_id}'.") from exc
    except QDError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
async def search_gazettes(
    ctx: Context[AppContext, None],
    query: str = "",
    territory_ids: list[str] | None = None,
    published_since: str | None = None,
    published_until: str | None = None,
    size: int = 10,
    offset: int = 0,
    sort_by: Literal["relevance", "descending_date", "ascending_date"] = "relevance",
) -> GazetteSearchResponse:
    """Search the text of published Brazilian municipal official gazettes.

    Each result is one gazette (one city's official publication, one edition, one
    date) with a short excerpt showing where `query` matched. This searches gazette
    *content*, not city metadata — resolve a city name to its territory_id with
    `search_cities` first.

    `query` uses OpenSearch's "simple query string syntax": bare words are OR'd
    together, a leading `+` requires a term, a leading `-` excludes it, and double
    quotes match an exact phrase — e.g. '"João da Silva"' for an exact name, or
    '+licitação +pregão' to require both terms together. An empty query returns
    matching gazettes' metadata without excerpts.

    `territory_ids` restricts the search to specific cities by their 7-digit IBGE ID
    (from `search_cities` or `get_city`); omit it to search across all available
    cities. `published_since` / `published_until` are inclusive ISO dates
    (YYYY-MM-DD) bounding the gazette's publication date — leave both unset to search
    the full available history. `size` is capped at 50 results per call; use `offset`
    to page through more. `sort_by` defaults to relevance; use "descending_date" or
    "ascending_date" to sort chronologically instead.

    Example: to find mentions of "Empresa X" in Porto Alegre gazettes published
    between January and July 2026, once territory_id "4314902" is known, call
    search_gazettes(query='"Empresa X"', territory_ids=["4314902"],
    published_since="2026-01-01", published_until="2026-07-31").
    """
    validated_ids = [_require_territory_id(t) for t in territory_ids] if territory_ids else None

    since = _parse_date("published_since", published_since)
    until = _parse_date("published_until", published_until)
    if since is not None and until is not None and since > until:
        raise ToolError(
            f"published_since ({published_since}) must not be after published_until ({published_until})."
        )

    if not 1 <= size <= MAX_GAZETTE_RESULT_SIZE:
        raise ToolError(f"size must be between 1 and {MAX_GAZETTE_RESULT_SIZE}, got {size}.")
    if offset < 0:
        raise ToolError(f"offset must be >= 0, got {offset}.")

    # sort_by is typed as Literal[...] above, so the MCP framework already rejects any
    # value outside the three SortBy members before this function runs.
    try:
        return await _client(ctx).search_gazettes(
            querystring=query,
            territory_ids=validated_ids,
            published_since=published_since,
            published_until=published_until,
            size=size,
            offset=offset,
            sort_by=SortBy(sort_by),
        )
    except QDError as exc:
        raise ToolError(str(exc)) from exc


def run() -> None:  # pragma: no cover - thin entry point, exercised manually / by MCP clients
    """Run the MCP server over stdio. Entry point for the `querido-diario-mcp-server` script."""
    mcp.run()
