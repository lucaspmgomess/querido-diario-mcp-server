"""Environment-driven configuration for the Querido Diário HTTP client."""

from __future__ import annotations

import os
from dataclasses import dataclass

from querido_diario_mcp_server import __version__

DEFAULT_BASE_URL = "https://api.queridodiario.ok.org.br"
"""Documented production base URL for the public Querido Diário API.

Source: https://docs.queridodiario.ok.org.br/en/latest/using/public-api.html and the
upstream FastAPI app at https://github.com/okfn-brasil/querido-diario-api. As of this
writing, live requests against this host return a generic 404 from what appears to be
an infrastructure/reverse-proxy layer rather than the FastAPI application itself; see
the README's "Upstream API status" section. The value is kept as the default because
it is the address the project documents and may recover independently of this code.
"""

USER_AGENT = f"querido-diario-mcp-server/{__version__} (+https://github.com/okfn-brasil/querido-diario-api)"

DEFAULT_CONNECT_TIMEOUT = 5.0
DEFAULT_READ_TIMEOUT = 15.0
DEFAULT_WRITE_TIMEOUT = 5.0
DEFAULT_POOL_TIMEOUT = 5.0


@dataclass(frozen=True, slots=True)
class ClientConfig:
    """Connection settings for `QueridoDiarioClient`."""

    base_url: str = DEFAULT_BASE_URL
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT
    read_timeout: float = DEFAULT_READ_TIMEOUT
    write_timeout: float = DEFAULT_WRITE_TIMEOUT
    pool_timeout: float = DEFAULT_POOL_TIMEOUT
    user_agent: str = USER_AGENT


def load_config() -> ClientConfig:
    """Build a `ClientConfig` from the environment.

    Only `QD_API_BASE_URL` is currently read; timeouts use conservative defaults
    that are not exposed as environment variables to keep the configuration surface
    small.
    """
    base_url = os.environ.get("QD_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    return ClientConfig(base_url=base_url)
