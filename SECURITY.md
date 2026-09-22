# Security Policy

## Supported versions

Security fixes are applied to the current released version and the latest code on the `main` branch.

## Reporting a vulnerability

Please do not report suspected vulnerabilities in a public GitHub issue.

Send a private report to **lucas.maurer@ufrgs.br** with the subject:

```text
[SECURITY] querido-diario-mcp-server
```

Include, when possible:

- the affected version or commit;
- a clear description of the issue;
- reproduction steps or a proof of concept;
- the security impact you expect;
- any suggested mitigation.

Avoid including real credentials, personal data or sensitive third-party data in the report.

## Security model

This project is intentionally read-only and local-first.

The server:

- calls only a small set of Querido Diário API endpoints;
- does not expose write operations;
- does not accept arbitrary target URLs from MCP tool callers;
- does not automatically dereference gazette URLs returned by the upstream API;
- validates territory IDs, dates, pagination and sort inputs;
- does not require user credentials or API keys;
- does not collect telemetry.

A report is especially relevant if it demonstrates a way to bypass these boundaries, cause unintended outbound requests, expose local data, leak sensitive response content, or execute code outside the expected MCP process model.

## Upstream issues

Problems that affect the public Querido Diário service itself, rather than this MCP server, should be reported to the appropriate upstream project or maintainer.
