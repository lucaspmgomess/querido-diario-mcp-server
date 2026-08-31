"""Environment-driven configuration for the Querido Diário HTTP client."""

from __future__ import annotations

import os
from dataclasses import dataclass

from querido_diario_mcp_server import __version__

DEFAULT_BASE_URL = "https://api.queridodiario.org.br"
"""Current production base URL for the public Querido Diário API.

Derived from the official production deployment configuration at
https://github.com/okfn-brasil/querido-diario-deployment
(`k8s/overlays/production/kustomization.yaml`, which sets `QD_API_URL` and patches the
frontend's `env.js` to this same host), and independently confirmed live: `/health`,
`/cities`, and `/gazettes` all return correct FastAPI JSON responses, including real
historical gazette data. The older `api.queridodiario.ok.org.br` host is legacy — its
DNS and TLS certificate are still live, but every path on it returns a generic,
non-FastAPI 404, and the frontend served from the corresponding `queridodiario.ok.org.br`
is a stale, separately-hosted (Netlify) deployment, not the current production site. See
the README's "Upstream API status" section for the full evidence trail.
"""

USER_AGENT = f"querido-diario-mcp-server/{__version__} (+https://github.com/okfn-brasil/querido-diario-api)"

DEFAULT_CONNECT_TIMEOUT = 5.0
DEFAULT_READ_TIMEOUT = 30.0
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
