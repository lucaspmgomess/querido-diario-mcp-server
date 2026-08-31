# querido-diario-mcp-server

<!-- mcp-name: io.github.lucaspmgomess/querido-diario-mcp-server -->

> **Community-built, unofficial** open-source MCP server for the [Querido Diário](https://queridodiario.org.br) public API. Querido Diário is a project of [Open Knowledge Brasil](https://ok.org.br/). This repository is **not** an official Open Knowledge Brasil project unless explicitly adopted by the organization, and is not affiliated with, endorsed by, or supported by it. It sends nothing anywhere except read-only HTTPS requests to the public Querido Diário API — no telemetry, no accounts, no proprietary backend.

A local-first [Model Context Protocol](https://modelcontextprotocol.io) server that gives MCP clients (Claude, Cursor, Codex, and others) read-only, structured access to Brazilian municipal official gazettes indexed by Querido Diário.

## Quick Start

Requires [uv](https://docs.astral.sh/uv/) (which provides `uvx`) and Python 3.12+. No repository clone needed — `uvx` fetches the published package from PyPI and runs it:

```bash
uvx querido-diario-mcp-server
```

This starts the MCP server on stdio. It produces no interactive output by design — it's meant to be launched by an MCP client (see [Client configuration](#client-configuration)), not run standalone in a terminal.

## Client configuration

Each of these uses the same `uvx querido-diario-mcp-server` command; only the config file format differs.

### Claude Desktop / Claude Code

Add to `claude_desktop_config.json` (Claude Desktop) or a project-level `.mcp.json` (Claude Code):

```json
{
  "mcpServers": {
    "querido-diario": {
      "command": "uvx",
      "args": ["querido-diario-mcp-server"]
    }
  }
}
```

### Cursor

Add the same shape to `.cursor/mcp.json` (project-level) or your global Cursor MCP settings:

```json
{
  "mcpServers": {
    "querido-diario": {
      "command": "uvx",
      "args": ["querido-diario-mcp-server"]
    }
  }
}
```

### Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.querido-diario]
command = "uvx"
args = ["querido-diario-mcp-server"]
```

### Other stdio-based MCP clients

Any client that launches MCP servers as a local stdio subprocess can use the same command (`uvx`) and argument (`querido-diario-mcp-server`) — consult that client's own configuration docs for the exact file/key names.

## Tools

Only three tools are exposed, all read-only.

| Tool | Purpose |
|---|---|
| `search_cities` | Find Brazilian municipalities by (partial) name and resolve their 7-digit IBGE territory ID. Optional `state_code` filter. |
| `get_city` | Fetch one municipality's details by its exact 7-digit IBGE territory ID. |
| `search_gazettes` | Full-text search over published gazette content, filterable by city, publication date range, page size/offset, and sort order. |

`search_gazettes` uses OpenSearch's ["simple query string" syntax](https://opensearch.org/docs/latest/query-dsl/full-text/simple-query-string/) upstream: bare words are OR'd together, `+term` requires a term, `-term` excludes it, and `"exact phrase"` matches literally — e.g. `'"João da Silva"'` for an exact name.

## Examples

```
User: "Find mentions of ACME Ltda in Porto Alegre gazettes from January to July 2026."

1. search_cities(city_name="Porto Alegre")            -> resolves territory_id "4314902"
2. search_gazettes(
       query='"ACME Ltda"',
       territory_ids=["4314902"],
       published_since="2026-01-01",
       published_until="2026-07-31",
   )
```

Other things you can ask an MCP client connected to this server:

- "Which Querido Diário municipality entry corresponds to Torres, RS?"
- "Search for public procurement references to artificial intelligence in Porto Alegre gazettes."
- "Get the Querido Diário entry for IBGE territory ID 3550308."

## Architecture

```
src/querido_diario_mcp_server/
    __init__.py   # package version + main() entry point
    config.py     # environment-driven configuration (QD_API_BASE_URL, timeouts)
    errors.py     # QDError exception hierarchy (integration-level failures)
    models.py     # Pydantic domain models mirroring the upstream API contract
    client.py     # async httpx client for the Querido Diário HTTP API — no MCP imports
    server.py     # MCP protocol boundary: MCPServer instance, lifespan, tool definitions
```

`client.py` knows nothing about the Model Context Protocol; it is a small, typed wrapper around three upstream endpoints that can be tested entirely with `httpx.MockTransport`. `server.py` is the only module that imports the MCP SDK: it validates tool arguments, translates `QDError`s into `ToolError`s an LLM can read and self-correct from, and returns typed structured output. A single `httpx.AsyncClient` connection pool is created once, in the server's lifespan, and reused across every tool call.

There is another repository, [`mcp-dir/querido_diario-mcp`](https://github.com/mcp-dir/querido_diario-mcp), that points MCP clients at a proprietary hosted implementation. This project is deliberately different: the actual server implementation is open source and runs locally as a subprocess you launch yourself — no account, API key, or hosted proxy involved — and calls the public Querido Diário API directly over plain `httpx`.

## Security / read-only design

- This server only issues `GET` requests to a small, fixed set of upstream endpoints. It has no write path anywhere.
- It never fetches an arbitrary URL supplied by a tool caller, and it never automatically dereferences the `url` / `txt_url` fields the upstream API returns for a gazette — doing either would be a server-side request forgery (SSRF) primitive. Following those links, if you need the full gazette text, is left to the client/user.
- All tool arguments are validated before use: territory IDs must be exactly 7 digits, dates must parse as ISO `YYYY-MM-DD` with `published_since <= published_until`, `size` is capped, `offset` must be non-negative, and `sort_by` is constrained to the three values the upstream API accepts.
- Upstream error bodies are never forwarded verbatim — HTML error pages and oversized bodies are replaced with a short, safe summary before reaching an MCP client.
- No secrets, credentials, or telemetry are involved; the only configuration is the API base URL.

Deliberately not implemented in this phase: arbitrary URL fetching, full gazette text/PDF download, OCR, write operations of any kind, a database, crawling or background jobs, LLM summarization, and a web interface — these are simply out of scope for a deliberately small, focused server, not oversights.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `QD_API_BASE_URL` | `https://api.queridodiario.org.br` | Base URL of the Querido Diário API. Override to point at a local/staging instance. |

## Development

Local development requires cloning the repository (Quick Start above does not).

```bash
git clone https://github.com/lucaspmgomess/querido-diario-mcp-server.git
cd querido-diario-mcp-server
uv sync                          # install runtime + dev dependencies
uv run ruff check .              # lint
uv run ruff format --check .     # formatting check
uv run pyright                   # static type checking (strict mode)
uv run pytest --cov              # test suite, with coverage
```

The four checks above (everything but `uv sync`) all must pass before a change is considered complete; this is exactly what CI runs.

To run the server from a local checkout instead of the published package: `uv run querido-diario-mcp-server`.

To poke at the tools interactively during development, use the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector):

```bash
uv run mcp dev src/querido_diario_mcp_server/server.py:mcp
```

### Tests

Unit tests for `client.py` mock the HTTP boundary with `httpx.MockTransport` — no test depends on network access or a live Querido Diário instance. They cover successful requests, query parameter serialization (repeated `territory_ids`, exact query-string preservation, date ranges, pagination, sorting), empty results, and upstream failure modes (404, 400/422, 5xx, malformed/non-JSON bodies, timeouts, connection errors).

Integration tests for `server.py` drive the real `MCPServer` instance through the MCP SDK's in-process `Client` (no subprocess, no open port) and assert on tool discoverability, input schemas, structured tool output, and that both input-validation failures and upstream integration failures surface as clean MCP tool errors rather than raw Python tracebacks or leaked HTML error pages.

### Manual live smoke tests

Two small, manual-only scripts hit the real production API — neither is part of the automated suite, and neither runs in CI:

```bash
uv run python scripts/smoke_test_api.py   # QueridoDiarioClient -> production API only
uv run python scripts/smoke_test_mcp.py   # full MCP client -> tool -> client -> API path
```

Use them by hand to re-verify the upstream API (and, for the second script, the full MCP protocol path) after a suspected outage or domain change.

## Upstream API notes

`QD_API_BASE_URL` defaults to `https://api.queridodiario.org.br`, derived from the official production deployment configuration in [`okfn-brasil/querido-diario-deployment`](https://github.com/okfn-brasil/querido-diario-deployment) and confirmed live (`/health`, `/cities`, `/gazettes` all return correct data, including real historical gazettes). An older `api.queridodiario.ok.org.br` host still resolves but no longer serves the API — see [`docs/upstream-api-history.md`](./docs/upstream-api-history.md) for the full investigation if you need it.

This project calls the public Querido Diário API but does not vendor or copy any of its implementation. Querido Diário is built and maintained by [Open Knowledge Brasil](https://ok.org.br/) and its community; see [okfn-brasil/querido-diario](https://github.com/okfn-brasil/querido-diario) (scrapers) and [okfn-brasil/querido-diario-api](https://github.com/okfn-brasil/querido-diario-api) (public API) for the upstream project this server integrates with.

## Contributing

Issues and pull requests are welcome. Please run the full check suite (`ruff check`, `ruff format --check`, `pyright`, `pytest --cov`) before opening a PR, and keep new tools/behavior scoped to what's documented above — this project intentionally stays small.

## License

[MIT](./LICENSE)
