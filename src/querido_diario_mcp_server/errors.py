"""Exception hierarchy for the Querido Diário integration layer.

Every failure mode of `QueridoDiarioClient` surfaces as a subclass of `QDError`, so
callers (notably the MCP tool layer in `server.py`) can catch one type and still get
enough detail to report a useful, non-leaky message back to an MCP client.
"""

from __future__ import annotations


class QDError(Exception):
    """Base class for all Querido Diário integration errors."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class QDConnectionError(QDError):
    """Could not reach the Querido Diário API (DNS, TCP, or TLS failure)."""


class QDTimeoutError(QDError):
    """The Querido Diário API did not respond within the configured timeout."""


class QDNotFoundError(QDError):
    """The requested resource does not exist upstream (HTTP 404)."""


class QDBadRequestError(QDError):
    """The Querido Diário API rejected the request as invalid (HTTP 400/422)."""


class QDServerError(QDError):
    """The Querido Diário API reported a server-side failure (HTTP 5xx)."""


class QDResponseParsingError(QDError):
    """The Querido Diário API returned a response that could not be parsed as expected.

    Covers non-JSON bodies (e.g. an HTML error page from a proxy in front of the API)
    and JSON that does not match the documented response schema.
    """
