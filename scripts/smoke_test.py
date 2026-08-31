"""Manual, live smoke test against the real Querido Diário production API.

Not part of the automated test suite and not run in CI — pytest never touches the
network. Run this by hand after a suspected upstream change (a new domain, an
outage, a schema change) to quickly check whether `search_cities` and
`search_gazettes` still work end to end against the real API:

    uv run python scripts/smoke_test.py

Respects `QD_API_BASE_URL` if set, otherwise uses the client's default. Exits
non-zero on any failure.
"""

from __future__ import annotations

import asyncio
import sys

from querido_diario_mcp_server.client import QueridoDiarioClient
from querido_diario_mcp_server.config import load_config
from querido_diario_mcp_server.errors import QDError


async def main() -> int:
    config = load_config()
    print(f"Smoke-testing {config.base_url} ...")

    async with QueridoDiarioClient(config=config) as client:
        try:
            cities = await client.search_cities("Porto Alegre")
        except QDError as exc:
            print(f"FAIL: search_cities raised {type(exc).__name__}: {exc}")
            return 1

        matches = [c for c in cities.cities if c.state_code == "RS"]
        if not matches:
            print(f"FAIL: search_cities returned no Porto Alegre (RS) match: {cities.cities}")
            return 1
        territory_id = matches[0].territory_id
        print(f"OK: search_cities resolved Porto Alegre, RS -> territory_id={territory_id}")

        try:
            gazettes = await client.search_gazettes(territory_ids=[territory_id], size=1)
        except QDError as exc:
            print(f"FAIL: search_gazettes raised {type(exc).__name__}: {exc}")
            return 1
        print(f"OK: search_gazettes returned total_gazettes={gazettes.total_gazettes}")

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
