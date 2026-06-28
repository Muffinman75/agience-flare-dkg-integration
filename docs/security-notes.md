# Security Notes

## Credential model

All credentials are read from environment variables — never hardcoded or logged.

- `DKG_TOKEN` — bearer token for the MCP-fronted DKG node HTTP API (MCP transport only)
- `DKG_DAEMON_TOKEN` — bearer token for the local DKG v10 daemon HTTP API (daemon transport). Auto-loaded from `~/.dkg/auth.token` if unset.
- `DKG_BASE_URL` — base URL for the DKG node or daemon (daemon default: `http://127.0.0.1:9201`; MCP default `http://localhost:8083` when running alongside Agience backend on `8081`)
- `DKG_TRANSPORT` — selects transport (`daemon` or `mcp`). Override per-call with `--transport`.
- `AGIENCE_TOKEN` — Agience scoped API key (`agc_...`), only required when using `--from-agience-artifact` to fetch governed artifacts before projection

No Agience platform credentials are required for direct CLI writes (`wm-write` with explicit `--content`). They are only needed when fetching committed artifacts from the Agience governance layer. FLARE service credentials are only used when `retrieval_profile = protected-search` is explicitly configured by the operator — this mode is not enabled by default.

## Agience Core policy model

The Agience Core platform includes a `PolicyMappingRecord` that governs what content reaches DKG:

- `policy_class` determines the confidentiality level (internal-standard, internal-confidential, export-approved, public-verifiable)
- `export_profile` controls whether content can be projected (no-export, approval-required, derived-only, full-projection-allowed)
- `promotion_profile` limits DKG stage eligibility (none, wm-only, swm-eligible, vm-eligible)
- `retrieval_profile` routes retrieval through Agience, FLARE, or both (native-search, protected-search, mixed-search)

Projection validation (`validate_projection_request()`) enforces that artifacts must be committed, pass export policy, and have an approval receipt before any content reaches DKG.

## FLARE confidential retrieval boundary

When `retrieval_profile = protected-search`, FLARE mediates the retrieval path with cryptographic enforcement:

- Per-cell AES-256-GCM encryption with HKDF-derived keys
- Shamir K-of-M threshold oracle key issuance — no single host compromise yields the master key
- Ed25519 signed grant ledger with hash-chained tamper evidence
- Only derived summaries or claim projections reach DKG; raw content stays encrypted

## Declared network egress

All external domains contacted by this package:

1. **DKG endpoint** — the `DKG_BASE_URL` value. With daemon transport this is the local DKG v10 daemon (default `http://127.0.0.1:9201`); with MCP transport it is a DKG node exposing `POST /mcp`. This is the only endpoint contacted in the default configuration.
2. **Agience platform endpoint** — only when `--from-agience-artifact` is used; contacts `AGIENCE_BASE_URL` to fetch a governed artifact before projection. The hosted default is `https://my.agience.ai`; operators may point this at a self-hosted Agience instead.
3. **FLARE service endpoint** — only when the operator explicitly enables `protected-search` mode. Disabled by default. When enabled, only derived summary/claim projections are written to DKG; raw artifact content remains FLARE-protected.

No other external domains are contacted. No telemetry, no analytics endpoints, no remote module loading.

## Declared DKG write authority

Every DKG endpoint invoked by this package, across both supported public interfaces (bounty § 5):

### Daemon HTTP API (canonical)

| Endpoint | Operation | Authority |
|---|---|---|
| `GET /api/status` / `GET /health` | Health check | Read-only |
| `POST /api/knowledge-assets` | Create KA + open WM draft (atomic create+write) | Write (WM) |
| `POST /api/knowledge-assets/{name}/wm/write` | Append quads to the WM draft | Write (WM) |
| `POST /api/shared-memory/write` (`localOnly=true`) | Write Working Memory layer (direct SWM path) | Write (WM) |
| `POST /api/shared-memory/write` (`localOnly=false`) | Write Shared Memory layer | **Curator-authorized (SHARE)** |
| `POST /api/knowledge-assets/{name}/swm/share` | Share Working → Shared Memory (v10.0.1 operation historically called `promote`) | **Curator-authorized (SHARE)** |
| `POST /api/knowledge-assets/{name}/vm/publish` | Publish to Verifiable Memory (on-chain) | **Curator-authorized (PUBLISH)** |
| `POST /api/query` | SPARQL search across named sub-graphs | Read-only |

_As of DKG `v10.0.1` (first introduced in `v10.0.0-rc.17`) the daemon retired the `/api/assertion/*` routes for this unified `/api/knowledge-assets` surface (OT-RFC-43). The client falls back **once** to the legacy `/api/assertion/create`, `/api/assertion/{name}/write`, and `/api/assertion/{name}/promote` routes only if a pre-v10.0.1 daemon returns `404`._

### MCP Streamable HTTP

| Endpoint / Tool | Operation | Authority |
|---|---|---|
| `GET /health` | Health check | Read-only |
| `POST /mcp` → `dkg-create` (privacy=private) | Write Knowledge Asset to Working Memory | Write (WM) |
| `POST /mcp` → `dkg-create` (privacy=public) | Share to Shared Memory (SHARE) | **Curator-authorized (SHARE)** |
| `POST /mcp` → `dkg-sparql-query` | Search Working and/or Shared Memory | Read-only |

All SHARE operations are **always explicit and operator-initiated** — invoked only by the `agience-dkg share` CLI command (or backward-compatible `promote` alias) or the `agience_share` MCP tool (or `agience_promote` alias), never as a side effect of a write.

PUBLISH toward Verifiable Memory is likewise **always explicit and operator-initiated** — invoked only by the `agience-dkg vm-publish` CLI command (daemon transport only; no MCP equivalent, no background loop). It is never triggered by a WM write or SHARE.

## MCP stdio server

The `agience-dkg-mcp` entry point runs as an MCP stdio server. It reads `DKG_TOKEN`, `DKG_DAEMON_TOKEN`, `DKG_BASE_URL`, and `DKG_TRANSPORT` from environment variables only — credentials are never accepted as tool arguments. The server exposes three tools (`agience_wm_write`, `agience_share` [`agience_promote` alias], `agience_search`) that call through to either `DkgDaemonClient` or `DkgHttpClient` (selected by `DKG_TRANSPORT`) with the same security properties as the CLI.

## Curator authority stance

No SHARE or PUBLISH operation is invoked without explicit caller intent. The CLI `share` command (backward-compatible `promote` alias) requires the operator to pass a `turnUri` and `context_graph_id` explicitly, and maps to either `POST /api/knowledge-assets/{name}/swm/share` (daemon transport; legacy `POST /api/assertion/{name}/promote` only on `404` fallback) or `dkg-create` with `privacy=public` (MCP transport) — there is no background promotion loop. The `vm-publish` command similarly requires an explicit `turnUri` and on-chain-registered `context_graph_id`, and maps to `POST /api/knowledge-assets/{name}/vm/publish` (daemon only).

## Dynamic code loading

This package:
- does not fetch or execute remote code
- does not use `eval` on any external input
- does not import any internal DKG node packages (`@origintrail-official/dkg-core` or any non-public subpath)
- does not patch the DKG node daemon

## Package hygiene

- No `postinstall` or `preinstall` scripts
- MIT license, SPDX identifier `MIT`
- `pip-audit -r requirements-audit.txt` clean against direct dependencies (`httpx`, `pydantic`, `typer`, `python-dotenv`) — no known vulnerabilities as of 2026-05-13. CVEs reported in indirect deps of `pip-audit` itself (`authlib`, `urllib3`, `pytest`, `python-multipart`) are not transitive from this package.
- Dependencies pinned with lower bounds only (`httpx>=0.27`, `pydantic>=2.0,<3`, `typer>=0.12,<1`, `python-dotenv>=1.0`) for compatibility
- Published to PyPI as `agience-flare-dkg-integration==0.4.4` with build provenance via GitHub Actions (`pypa/gh-action-pypi-publish` with `attestations: true`); npm wrapper of the same name and version published with provenance via `actions/setup-node` + `npm publish --provenance`
