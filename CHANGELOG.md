# Changelog

All notable changes to this project are documented here.

The project follows semantic versioning for published package releases.

## Unreleased

### Added

- English-first project documentation with a maintained Portuguese translation.
- Contribution guidelines and pull request template.
- Security policy and private vulnerability-reporting guidance.
- Structured bug and feature request forms.
- Code of conduct.
- Dependabot configuration for Python and GitHub Actions dependencies.
- PEP 561 `py.typed` marker for typed package consumers.

### Changed

- Expanded CI coverage to Python 3.12 and 3.13.
- CI now validates the lockfile, MCP registry JSON, wheel and source distribution builds, and installed artifact smoke tests.
- GitHub Actions dependencies in CI are pinned to immutable commit SHAs.
- Package and MCP Registry metadata were refined for clearer discovery and positioning.
- Documentation was shortened and reorganized around quick start, tools, architecture, security and development.

### Security

- CI now uses explicit read-only repository permissions.
- Project documentation now makes the read-only and no-arbitrary-URL security boundaries explicit.

## 0.1.0 - 2026-08-31

Initial public release.

### Added

- Local-first MCP server over the public Querido Diário API.
- `search_cities` municipality discovery.
- `get_city` municipality lookup.
- `search_gazettes` full-text gazette search.
- Async HTTP client built with `httpx`.
- Typed Pydantic models and structured MCP outputs.
- Validation and integration-error handling.
- Ruff, strict Pyright and pytest coverage.
- GitHub Actions CI.
- PyPI distribution and MCP Registry publication.

[0.1.0]: https://github.com/lucaspmgomess/querido-diario-mcp-server/releases/tag/v0.1.0
