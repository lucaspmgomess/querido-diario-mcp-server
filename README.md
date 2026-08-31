# querido-diario-mcp-server

> **Community-built, unofficial** open-source MCP server for the [Querido Diário](https://queridodiario.ok.org.br) public API. Querido Diário is a project of [Open Knowledge Brasil](https://ok.org.br/). This repository is **not** an official Open Knowledge Brasil project unless explicitly adopted by the organization, and is not affiliated with, endorsed by, or supported by it.

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
| `QD_API_BASE_URL` | `https://api.queridodiario.ok.org.br` | Base URL of the Querido Diário API. Override to point at a local/staging instance (see [Upstream API status](#upstream-api-status)). |

## Upstream API status

The default base URL, `https://api.queridodiario.ok.org.br`, is the address documented at [docs.queridodiario.ok.org.br](https://docs.queridodiario.ok.org.br/en/latest/using/public-api.html), and it is independently confirmed by three sources, not just the docs page:

1. The live frontend's own `env.js` sets `window.__env.apiUrl = 'https://api.queridodiario.ok.org.br'`, and the checked-in source (`okfn-brasil/querido-diario-frontend`, `src/env.js` and `src/app/env.service.ts`) matches it byte for byte.
2. The frontend's HTTP services (e.g. `territory.service.ts`) build requests as `${apiUrl}/cities`, `${apiUrl}/cities/{id}` — bare paths, no `/api` or other prefix — exactly what this client sends.
3. The production Traefik `IngressRoute` in `okfn-brasil/querido-diario-deployment` (`k8s/base/api/ingressroute.yaml`) routes `Host(api.queridodiario.ok.org.br)`, any path, straight to the API service on port 8080, with no `PathPrefix` requirement; the production `ConfigMap` sets `QUERIDO_DIARIO_API_ROOT_PATH: ""`. There is also a same-domain `queridodiario.ok.org.br/api/*` route, but it's a 302 redirect to `https://api.queridodiario.ok.org.br/*` (see `api-redirect` middleware), not a second valid origin — so there is no undocumented path prefix or runtime override to find.

**As of this writing, live requests to every path implied by the above (`/health`, `/cities`, `/gazettes`, `/docs`, with and without an `/api` prefix) return a generic `404 page not found`** that does not match FastAPI's JSON-shaped 404 — it reads as Traefik's own "no router matched this request" fallback rather than a response from the FastAPI application itself, consistent with a DNS, TLS, or ingress-routing problem in front of the API rather than a wrong URL. This was verified by direct `curl` requests on 2026-08-31 (initial check) and reconfirmed on the same date after this investigation; it is infrastructure this codebase cannot fix, and no alternative endpoint is documented or evidenced anywhere in the upstream source, so none is guessed here.

Because of this, the request/response contract implemented in `client.py` and `models.py` was verified against the **upstream FastAPI source** at [`okfn-brasil/querido-diario-api`](https://github.com/okfn-brasil/querido-diario-api) (`api/api.py`) rather than a live Swagger UI, per that repository being the authoritative contract when the hosted docs/API are unreachable. If you have access to a working instance (production, once the outage above is resolved, or a local instance per the upstream repos' own setup docs), point `QD_API_BASE_URL` at it and the client works unchanged.

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
