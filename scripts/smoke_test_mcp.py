"""Manual, live smoke test of the full MCP protocol path against production.

Exercises MCP client -> MCP tool -> `QueridoDiarioClient` -> the real Querido
Diário production API, using the MCP SDK's in-process `Client` (no subprocess,
no open port). This is the layer `scripts/smoke_test_api.py` does not cover.

Not part of the automated test suite and not run in CI — pytest never touches the
network. Run this by hand to confirm the server actually works end to end as an
MCP tool, not just as an HTTP client:

    uv run python scripts/smoke_test_mcp.py

Respects `QD_API_BASE_URL` if set, otherwise uses the client's default. Exits
non-zero on any failure.
"""

from __future__ import annotations

import asyncio
import sys

from mcp.client.client import Client

from querido_diario_mcp_server.server import mcp


async def main() -> int:
    async with Client(mcp, read_timeout_seconds=40) as client:
        tools = await client.list_tools()
        names = sorted(t.name for t in tools.tools)
        print(f"tools discovered: {names}")

        r1 = await client.call_tool("search_cities", {"city_name": "Porto Alegre", "state_code": "RS"})
        if r1.is_error or not r1.structured_content or not r1.structured_content.get("cities"):
            print(f"FAIL: search_cities tool call failed or returned no city: {r1.content}")
            return 1
        territory_id = r1.structured_content["cities"][0]["territory_id"]
        print(f"OK: search_cities tool resolved Porto Alegre, RS -> territory_id={territory_id}")

        r2 = await client.call_tool(
            "search_gazettes",
            {"territory_ids": [territory_id], "size": 1, "sort_by": "descending_date"},
        )
        if r2.is_error or r2.structured_content is None:
            print(f"FAIL: search_gazettes tool call failed: {r2.content}")
            return 1
        total = r2.structured_content.get("total_gazettes")
        print(f"OK: search_gazettes tool returned total_gazettes={total}")

    print("MCP end-to-end smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
