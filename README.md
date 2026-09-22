# Querido Diário MCP Server

<!-- mcp-name: io.github.lucaspmgomess/querido-diario-mcp-server -->

[![PyPI](https://img.shields.io/pypi/v/querido-diario-mcp-server.svg)](https://pypi.org/project/querido-diario-mcp-server/)
[![Python](https://img.shields.io/pypi/pyversions/querido-diario-mcp-server.svg)](https://pypi.org/project/querido-diario-mcp-server/)
[![CI](https://github.com/lucaspmgomess/querido-diario-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/lucaspmgomess/querido-diario-mcp-server/actions/workflows/ci.yml)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-published-brightgreen)](https://registry.modelcontextprotocol.io/?q=io.github.lucaspmgomess%2Fquerido-diario-mcp-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

A local-first [Model Context Protocol](https://modelcontextprotocol.io) server that gives AI clients structured, read-only access to Brazilian municipal official gazettes indexed by [Querido Diário](https://queridodiario.org.br).

**No API key · Runs locally · Read-only · No telemetry · Open source**

> 🇧🇷 [Versão em português](./README.pt-BR.md)

The package is published on [PyPI](https://pypi.org/project/querido-diario-mcp-server/) and the [MCP Registry](https://registry.modelcontextprotocol.io/?q=io.github.lucaspmgomess%2Fquerido-diario-mcp-server).

## What it does

Querido Diário provides searchable municipal official gazettes through a public API. This server exposes a small, typed MCP interface on top of that API so an MCP client can:

- resolve Brazilian municipalities and their IBGE territory IDs;
- search indexed official gazettes by text, municipality and date range;
- receive structured results that are easier for agents to inspect and combine with other tools.

The server runs as a local `stdio` subprocess and only performs read-only HTTPS requests to the public Querido Diário API.

## Quick start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

No repository clone is required:

```bash
uvx querido-diario-mcp-server
```

This starts the MCP server on `stdio`. It is intended to be launched by an MCP client rather than used as an interactive terminal application.

## Client configuration

All supported clients use the same command:

```text
uvx querido-diario-mcp-server
```

### Claude Desktop / Claude Code

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

Use this in `claude_desktop_config.json` for Claude Desktop or a project-level `.mcp.json` for Claude Code.

### Cursor

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

Add it to `.cursor/mcp.json` or your global Cursor MCP configuration.

### Codex CLI

```toml
[mcp_servers.querido-diario]
command = "uvx"
args = ["querido-diario-mcp-server"]
```

Other MCP clients that support local `stdio` servers can launch the same command.

## Tools

The server intentionally exposes a small, read-only tool surface.

| Tool | Purpose |
| --- | --- |
| `search_cities` | Search Brazilian municipalities by name and resolve the 7-digit IBGE territory ID. Supports an optional state filter. |
| `get_city` | Fetch one municipality by its exact 7-digit IBGE territory ID. |
| `search_gazettes` | Full-text search over indexed gazettes with municipality, publication date, pagination and sorting filters. |

`search_gazettes` uses the simple-query-string syntax supported by the upstream search API. Examples include `+required`, `-excluded` and `"exact phrase"`.

## Example

A user can ask:

```text
Find mentions of ACME Ltda in Porto Alegre gazettes
from January through July 2026.
```

An MCP client can then execute:

```text
1. search_cities(city_name="Porto Alegre")
   -> territory_id: "4314902"

2. search_gazettes(
       query='"ACME Ltda"',
       territory_ids=["4314902"],
       published_since="2026-01-01",
       published_until="2026-07-31",
   )
```

The result is returned as structured tool output for the client to summarize, filter or combine with other tools.

## Architecture

```text
MCP client
   |
   | stdio / MCP
   v
server.py
   |
   | validated tool arguments
   v
client.py
   |
   | typed read-only HTTPS requests
   v
Querido Diário public API
```

The implementation keeps the protocol boundary separate from the HTTP integration:

```text
src/querido_diario_mcp_server/
    __init__.py   package version and CLI entry point
    config.py     environment-driven configuration
    errors.py     integration error hierarchy
    models.py     typed Pydantic domain models
    client.py     async HTTP client with no MCP dependency
    server.py     MCP lifespan, validation and tool definitions
```

A single `httpx.AsyncClient` connection pool is created for the server lifecycle and reused across tool calls. The HTTP client can be tested independently of MCP, while integration tests exercise the real MCP server in process.

## Design principles

- **Read-only by design.** The integration only calls a fixed set of upstream GET endpoints.
- **Local-first.** There is no hosted middleware, proprietary backend or account requirement.
- **Typed boundaries.** API responses and MCP outputs use explicit Pydantic models.
- **Small tool surface.** The server exposes only the operations required to discover cities and search gazettes.
- **Explicit failures.** Upstream failures are converted to concise MCP tool errors rather than raw tracebacks or HTML responses.
- **No arbitrary URL fetching.** Tool callers cannot turn the server into a generic HTTP or SSRF primitive.
- **No telemetry.** The server does not collect usage data.

## Security

The server never automatically follows gazette URLs returned by the upstream API and does not accept arbitrary target URLs from tool callers. Territory IDs, dates, pagination and sort options are validated before use.

For vulnerability reporting and the supported security scope, see [SECURITY.md](./SECURITY.md).

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `QD_API_BASE_URL` | `https://api.queridodiario.org.br` | Base URL for the Querido Diário API. Can be overridden for local or staging environments. |

Normal users do not need to set any environment variables.

## Development

Clone the repository only if you want to contribute or work on the implementation:

```bash
git clone https://github.com/lucaspmgomess/querido-diario-mcp-server.git
cd querido-diario-mcp-server
uv sync
```

Run the same checks enforced by CI:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest --cov
```

Run the server from the checkout:

```bash
uv run querido-diario-mcp-server
```

Inspect the MCP tools interactively:

```bash
uv run mcp dev src/querido_diario_mcp_server/server.py:mcp
```

### Test strategy

Unit tests mock the HTTP boundary with `httpx.MockTransport`, so the automated suite does not depend on the public API.

Coverage includes:

- successful city and gazette searches;
- query serialization and repeated territory IDs;
- date ranges, pagination and sorting;
- empty result sets;
- 4xx and 5xx upstream failures;
- malformed responses;
- connection errors and timeouts;
- MCP tool discovery, schemas and structured outputs;
- validation errors and upstream failures at the MCP boundary.

Manual smoke-test scripts are available for validating the real production API and the full MCP-to-API path:

```bash
uv run python scripts/smoke_test_api.py
uv run python scripts/smoke_test_mcp.py
```

## Project status

The project is currently in beta. The MCP tool surface is intentionally small and changes are kept conservative.

The following are intentionally outside the current scope:

- arbitrary URL fetching;
- automatic PDF or full-text download;
- OCR;
- write operations;
- crawling and background jobs;
- built-in LLM summarization;
- a web interface.

## Relationship to Querido Diário

This is a community-built, unofficial project.

[Querido Diário](https://queridodiario.org.br) is maintained by [Open Knowledge Brasil](https://ok.org.br/) and its community. This repository is not an official Open Knowledge Brasil project, is not endorsed or maintained by the organization, and only consumes the project's public API.

Relevant upstream repositories:

- [okfn-brasil/querido-diario](https://github.com/okfn-brasil/querido-diario)
- [okfn-brasil/querido-diario-api](https://github.com/okfn-brasil/querido-diario-api)
- [okfn-brasil/querido-diario-deployment](https://github.com/okfn-brasil/querido-diario-deployment)

Additional notes about upstream endpoint history are kept in [docs/upstream-api-history.md](./docs/upstream-api-history.md).

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md) for the development workflow, project scope and review checklist.

## License

[MIT](./LICENSE)
