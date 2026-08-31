# querido-diario-mcp-server

> **Community-built, unofficial** open-source MCP server for the [Querido Diário](https://queridodiario.org.br) public API. Querido Diário is a project of [Open Knowledge Brasil](https://ok.org.br/). This repository is **not** an official Open Knowledge Brasil project unless explicitly adopted by the organization, and is not affiliated with, endorsed by, or supported by it.

A local-first [Model Context Protocol](https://modelcontextprotocol.io) server that gives MCP clients (Claude, Cursor, Codex, and others) read-only, structured access to Brazilian municipal official gazettes indexed by Querido Diário — without a hosted backend, a platform login, or a proprietary service in between.

## Why this exists

There is another repository, [`mcp-dir/querido_diario-mcp`](https://github.com/mcp-dir/querido_diario-mcp), that points MCP clients at a proprietary hosted implementation. This project is different on purpose:

- **The actual server implementation is open source** — every line that talks to the Querido Diário API and to the MCP protocol is in this repository, not behind someone else's endpoint.
- **Local-first.** You run the process yourself (`uv run querido-diario-mcp-server`); there is no account, API key, or hosted proxy involved.
- **It calls the public Querido Diário API directly**, over plain `httpx`, using the same endpoints documented at [docs.queridodiario.ok.org.br](https://docs.queridodiario.ok.org.br/en/latest/using/public-api.html).
- **Transparent architecture.** The HTTP integration (`client.py`) is fully decoupled from the MCP protocol boundary (`server.py`) and is unit-testable without a network connection.
- **Typed end to end.** Pydantic models for every request/response shape, strict Pyright checking, and a clean, purpose-built exception hierarchy instead of raw dictionaries and stringly-typed errors.
- **Deliberately small.** Three focused tools, not twenty. See [Limitations](#limitations) for what is intentionally out of scope.

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

## Tools

Only three tools are exposed, all read-only.

| Tool | Purpose |
|---|---|
| `search_cities` | Find Brazilian municipalities by (partial) name and resolve their 7-digit IBGE territory ID. Optional `state_code` filter. |
| `get_city` | Fetch one municipality's details by its exact 7-digit IBGE territory ID. |
| `search_gazettes` | Full-text search over published gazette content, filterable by city, publication date range, page size/offset, and sort order. |

`search_gazettes` uses OpenSearch's ["simple query string" syntax](https://opensearch.org/docs/latest/query-dsl/full-text/simple-query-string/) upstream: bare words are OR'd together, `+term` requires a term, `-term` excludes it, and `"exact phrase"` matches literally — e.g. `'"João da Silva"'` for an exact name.

### Example interaction

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

## Installation

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12 (uv will install the interpreter for you if it's missing).

```bash
git clone https://github.com/lucaspmgomess/querido-diario-mcp-server.git
cd querido-diario-mcp-server
uv sync
uv run pytest
```

## Running it

```bash
uv run querido-diario-mcp-server
```

This starts the server on stdio, the transport MCP desktop clients expect. It has no interactive output by design — it's meant to be launched by an MCP client, not run standalone in a terminal.

### MCP Inspector

To poke at the tools interactively during development:

```bash
uv run mcp dev src/querido_diario_mcp_server/server.py:mcp
```

This opens the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) in your browser, connected to this server over stdio.

### Claude Desktop / Claude Code

Add to your MCP client configuration (Claude Desktop's `claude_desktop_config.json`, or a project-level `.mcp.json` for Claude Code):

```json
{
  "mcpServers": {
    "querido-diario": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/querido-diario-mcp-server", "run", "querido-diario-mcp-server"]
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
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/querido-diario-mcp-server", "run", "querido-diario-mcp-server"]
    }
  }
}
```

### Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.querido-diario]
command = "uv"
args = ["--directory", "/absolute/path/to/querido-diario-mcp-server", "run", "querido-diario-mcp-server"]
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `QD_API_BASE_URL` | `https://api.queridodiario.org.br` | Base URL of the Querido Diário API. Override to point at a local/staging instance (see [Upstream API status](#upstream-api-status)). |

## Upstream API status

The default base URL, `https://api.queridodiario.org.br`, is derived directly from the official production deployment configuration, not guessed:

- [`okfn-brasil/querido-diario-deployment`](https://github.com/okfn-brasil/querido-diario-deployment)'s `k8s/overlays/production/kustomization.yaml` sets `DOMAIN: queridodiario.org.br` and `QD_API_URL: https://api.queridodiario.org.br` on the production `ConfigMap`, patches the frontend's `env.js` to the same `apiUrl`, and defines the production Traefik `IngressRoute` matching `Host(api.queridodiario.org.br)` → the `api` service, port 8080, no path prefix.
- The currently deployed frontend at `https://queridodiario.org.br/env.js` matches that configuration exactly (`apiUrl = 'https://api.queridodiario.org.br'`), and its `Last-Modified` header is recent, consistent with an actively maintained deployment.
- Live requests confirm it: `/health`, `/cities`, `/cities?city_name=...`, and `/gazettes` all return correct, well-formed FastAPI JSON — including real historical gazette data (e.g. Porto Alegre alone has 10,000+ indexed gazettes going back to 2022). `/gazettes` searches can be slow (~20-30s observed for a real query), which is why this client's default read timeout is 30s.

The older `api.queridodiario.ok.org.br` host (this project's previous default) is legacy: its DNS and Let's Encrypt certificate are still live, but every path on it returns a generic, non-FastAPI `404 page not found` — consistent with an ingress/routing layer with no active route, not the FastAPI app itself. The frontend at the corresponding `queridodiario.ok.org.br` also still resolves, but the `Server`/cache headers show it being served from **Netlify**, a separate, evidently stale static deployment — not the current production site (which is Cloudflare-fronted, per the config above). A third-party MCP integration (`mcp.ai`'s `querido_diario_buscar` tool) independently reports its own Querido Diário upstream call failing with an explicit "HTTP 404" error today, corroborating that this class of failure is real and externally visible, not specific to this project's requests.

Given this, `QD_API_BASE_URL` now defaults to `https://api.queridodiario.org.br`. If you have reason to point at a different instance (a local dev deployment, or a future domain change), override the environment variable — the client works unchanged against any conformant instance.

## Development

```bash
uv sync                          # install runtime + dev dependencies
uv run ruff check .              # lint
uv run ruff format --check .     # formatting check
uv run pyright                   # static type checking (strict mode)
uv run pytest --cov              # test suite, with coverage
```

The four checks above (everything but `uv sync`) all must pass before a change is considered complete; this is exactly what CI runs.

## Tests

Unit tests for `client.py` mock the HTTP boundary with `httpx.MockTransport` — no test depends on network access or a live Querido Diário instance. They cover successful requests, query parameter serialization (repeated `territory_ids`, exact query-string preservation, date ranges, pagination, sorting), empty results, and upstream failure modes (404, 400/422, 5xx, malformed/non-JSON bodies, timeouts, connection errors).

Integration tests for `server.py` drive the real `MCPServer` instance through the MCP SDK's in-process `Client` (no subprocess, no open port) and assert on tool discoverability, input schemas, structured tool output, and that both input-validation failures and upstream integration failures surface as clean MCP tool errors rather than raw Python tracebacks or leaked HTML error pages.

### Manual live smoke test

`scripts/smoke_test.py` is a small, manual-only script that calls `search_cities` and `search_gazettes` against the real production API (respecting `QD_API_BASE_URL`). It is not part of the automated suite and never runs in CI — use it by hand to quickly re-verify the upstream API is reachable and returning sane data after a suspected outage or domain change:

```bash
uv run python scripts/smoke_test.py
```

## Security / read-only design

- This server only issues `GET` requests to a small, fixed set of upstream endpoints. It has no write path anywhere.
- It never fetches an arbitrary URL supplied by a tool caller, and it never automatically dereferences the `url` / `txt_url` fields the upstream API returns for a gazette — doing either would be a server-side request forgery (SSRF) primitive. Following those links, if you need the full gazette text, is left to the client/user.
- All tool arguments are validated before use: territory IDs must be exactly 7 digits, dates must parse as ISO `YYYY-MM-DD` with `published_since <= published_until`, `size` is capped, `offset` must be non-negative, and `sort_by` is constrained to the three values the upstream API accepts.
- Upstream error bodies are never forwarded verbatim — HTML error pages and oversized bodies are replaced with a short, safe summary before reaching an MCP client.
- No secrets, credentials, or telemetry are involved; the only configuration is the API base URL.

## Limitations

Deliberately not implemented in this phase: arbitrary URL fetching, full gazette text/PDF download, OCR, write operations of any kind, a database, crawling or background jobs, LLM summarization, and a web interface. `server.py`'s module docstring explains the read-only, no-arbitrary-fetch design specifically (see [Security / read-only design](#security--read-only-design) above); the rest are simply out of scope for a deliberately small, focused Phase 1 server.

## Attribution

This project calls the public Querido Diário API but does not vendor or copy any of its implementation. Querido Diário is built and maintained by [Open Knowledge Brasil](https://ok.org.br/) and its community; see [okfn-brasil/querido-diario](https://github.com/okfn-brasil/querido-diario) (scrapers) and [okfn-brasil/querido-diario-api](https://github.com/okfn-brasil/querido-diario-api) (public API) for the upstream project this server integrates with.

## Contributing

Issues and pull requests are welcome. Please run the full check suite (`ruff check`, `ruff format --check`, `pyright`, `pytest --cov`) before opening a PR, and keep new tools/behavior scoped to what's documented above — this project intentionally stays small.

## License

[MIT](./LICENSE)
