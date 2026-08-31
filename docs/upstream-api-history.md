# Upstream API domain migration — investigation notes

This is engineering history, kept for anyone who needs the evidence trail behind
the current `QD_API_BASE_URL` default. For the short, current-state summary, see
the README's "Upstream API notes" section.

## Timeline

- The project originally defaulted to `https://api.queridodiario.ok.org.br`, per
  the address documented at
  [docs.queridodiario.ok.org.br](https://docs.queridodiario.ok.org.br/en/latest/using/public-api.html)
  and the `apiUrl` baked into the `okfn-brasil/querido-diario-frontend` source at
  the time.
- Live requests to every path on that host (`/health`, `/cities`, `/gazettes`,
  `/docs`, with and without an `/api` prefix) returned a generic,
  non-FastAPI-shaped `404 page not found`.
- Direct inspection of `okfn-brasil/querido-diario-deployment`'s
  `k8s/overlays/production/kustomization.yaml` showed the production `ConfigMap`
  and Traefik `IngressRoute`s already targeting `queridodiario.org.br` /
  `api.queridodiario.org.br` — i.e. the migration to the new domain was already
  encoded in the deployment manifests.
- A deployment run from that period (`gh run view 30766827806 -R
  okfn-brasil/querido-diario-deployment --log-failed`) showed the `api`,
  `backend`, and `celery-worker` pods in `CrashLoopBackOff` (300+ restarts) and
  `deployment "api" exceeded its progress deadline` — a real, separate
  infrastructure incident around the same time as the domain cutover. No commits
  or workflow runs exist in that repository after that failure.

## Evidence the new domain is correct and live

- `queridodiario.org.br/env.js` matches the production kustomize overlay exactly
  (`apiUrl = 'https://api.queridodiario.org.br'`), with a recent
  `Last-Modified` header.
- Live requests to `api.queridodiario.org.br` return correct FastAPI JSON for
  `/health`, `/docs`, `/openapi.json`, `/cities`, `/cities?city_name=...`, and
  `/gazettes` — including real historical gazette data (e.g. Porto Alegre alone
  has 10,000+ indexed gazettes going back to 2022).
- Its TLS certificate is a Cloudflare-issued wildcard (`*.queridodiario.org.br`,
  Google Trust Services) issued only a few days before this was checked,
  consistent with an actively maintained, recently-fronted deployment.
- `/gazettes` searches were observed taking ~20-30s for a real query — this is
  why the client's default read timeout is 30s, not a symptom of a broken
  endpoint.

## Evidence the old domain is legacy

- `api.queridodiario.ok.org.br`'s DNS and Let's Encrypt certificate are still
  live, but every path returns the same generic 404 — consistent with an
  ingress/routing layer with no active route in front of it, not the FastAPI
  application itself.
- The frontend at the corresponding `queridodiario.ok.org.br` also still
  resolves, but its response headers (`cache-status: "Netlify Edge"`,
  `x-nf-request-id`) show it being served from Netlify — a separate, stale
  static deployment, not the current production site.
- A third-party MCP integration (`mcp.ai`'s `querido_diario_buscar` tool) was
  independently observed reporting its own Querido Diário upstream call failing
  with an explicit "HTTP 404" error, corroborating that this class of failure is
  real and externally visible, not specific to this project's requests.

## Conclusion

`QD_API_BASE_URL` defaults to `https://api.queridodiario.org.br`. The client
works unchanged against any conformant instance — override the environment
variable if you have reason to point elsewhere (a local dev deployment, or a
future domain change).
