# Contributing

Thanks for your interest in contributing to Querido Diário MCP Server.

The project intentionally keeps a small surface area: a local, read-only MCP interface over the public Querido Diário API. Changes should preserve that focus.

## Development setup

Requirements:

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- Git

Clone the repository and install the development environment:

```bash
git clone https://github.com/lucaspmgomess/querido-diario-mcp-server.git
cd querido-diario-mcp-server
uv sync
```

## Required checks

Before opening a pull request, run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest --cov
```

CI runs the same checks on the supported Python versions.

## Architecture boundaries

Please preserve the separation between the HTTP integration and the MCP protocol layer:

- `client.py` owns communication with the Querido Diário HTTP API and must not depend on MCP.
- `models.py` owns typed domain models.
- `server.py` owns MCP tools, lifecycle and protocol-facing validation.
- upstream integration failures should be translated into concise domain/MCP errors rather than leaking raw HTML responses or tracebacks.

## Project scope

Changes are a good fit when they improve:

- municipality discovery;
- gazette search and filtering;
- validation and structured outputs;
- reliability and error handling;
- test coverage;
- security of the read-only integration;
- compatibility with MCP clients;
- documentation and developer experience.

The following are intentionally outside the current scope unless discussed first:

- arbitrary URL fetching;
- write operations;
- web crawling;
- automatic PDF downloads or OCR;
- background-job infrastructure;
- built-in LLM summarization;
- a hosted proxy or proprietary backend;
- a web application.

For a substantial change, open an issue before investing in a large implementation.

## Tests

HTTP tests should use `httpx.MockTransport` or another deterministic local boundary. Automated tests must not depend on the production Querido Diário API.

MCP integration tests should exercise the real in-process server where practical and verify structured output as well as failure behavior.

Manual production smoke tests belong in `scripts/` and must not become a CI dependency.

## Pull requests

Keep pull requests focused and explain:

1. the problem being solved;
2. the behavior that changes;
3. how the change was tested;
4. whether the MCP tool schema or public behavior changes;
5. any security or compatibility implications.

A pull request should not include unrelated cleanup.

## Security

Do not open a public issue for a suspected vulnerability. Follow [SECURITY.md](./SECURITY.md).
