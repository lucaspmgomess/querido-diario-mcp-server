"""No-network smoke test for a *built* distribution (wheel or sdist).

Used by the release workflow to verify a built `dist/*.whl` or `dist/*.tar.gz`
actually installs and works, before it is ever uploaded to PyPI. Intended to run
in an isolated environment with the distribution installed as the only
dependency, e.g.:

    uv run --isolated --no-project --with dist/*.whl scripts/dist_smoke_test.py
    uv run --isolated --no-project --with dist/*.tar.gz scripts/dist_smoke_test.py

Makes no network calls: tool discovery uses the MCP SDK's in-process client, so
this is safe to run in CI. Exits non-zero on any failure.
"""

from __future__ import annotations

import asyncio
import sys


async def discover_tools() -> list[str]:
    from mcp.client.client import Client

    from querido_diario_mcp_server.server import mcp

    async with Client(mcp) as client:
        tools = await client.list_tools()
        return sorted(t.name for t in tools.tools)


def main() -> int:
    import querido_diario_mcp_server as pkg

    print(f"OK: imported querido_diario_mcp_server version {pkg.__version__}")

    names = asyncio.run(discover_tools())
    expected = ["get_city", "search_cities", "search_gazettes"]
    if names != expected:
        print(f"FAIL: expected tools {expected}, got {names}")
        return 1
    print(f"OK: exactly the expected tools are discoverable: {names}")

    print("Distribution smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
