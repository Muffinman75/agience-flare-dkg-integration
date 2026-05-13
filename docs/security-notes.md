# Security Notes

## Credential model

All credentials are read from environment variables — never hardcoded or logged.

- `DKG_TOKEN` — bearer token for the DKG v10 node HTTP API
- `DKG_BASE_URL` — base URL for the DKG node (default: `http://localhost:8083` when running alongside Agience backend on `8081`)
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

1. **DKG node endpoint** — the `DKG_BASE_URL` value (default: `http://localhost:8081`). This is the only endpoint contacted in the default configuration.
2. **FLARE service endpoint** — only when the operator explicitly enables `protected-search` mode. Disabled by default. When enabled, only derived summary/claim projections are written to DKG; raw artifact content remains FLARE-protected.

No other external domains are contacted. No telemetry, no analytics endpoints, no remote module loading.

## Declared DKG write authority

Every DKG endpoint invoked by this package:

| Endpoint / Tool | Operation | Authority |
|---|---|---|
| `GET /health` | Health check | Read-only |
| `POST /mcp` → `dkg-create` (privacy=private) | Write Knowledge Asset to Working Memory | Write (WM) |
| `POST /mcp` → `dkg-create` (privacy=public) | Promote to Shared Memory (SHARE) | **Curator-authorized (SHARE)** |
| `POST /mcp` → `dkg-sparql-query` | Search Working and/or Shared Memory | Read-only |

All write and search operations go through the **MCP Streamable HTTP transport** at `POST /mcp`. The SHARE operation (`dkg-create` with `privacy=public`) is **always explicit and operator-initiated**. It is never called automatically, silently, or as a side effect of a write operation.

PUBLISH toward Verified Memory is not invoked in this Round 1 package.

## MCP stdio server

The `agience-dkg-mcp` entry point runs as an MCP stdio server. It reads `DKG_TOKEN` and `DKG_BASE_URL` from environment variables only — credentials are never accepted as tool arguments. The server exposes three tools (`agience_wm_write`, `agience_promote`, `agience_search`) that call through to the `DkgHttpClient` with the same security properties as the CLI.

## Curator authority stance

No SHARE or PUBLISH operation is invoked without explicit caller intent. The CLI `promote` command requires the operator to pass a `turnUri` and `context_graph_id` explicitly, and maps to `dkg-create` with `privacy=public` — there is no background promotion loop.

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
- Published to PyPI as `agience-flare-dkg-integration==0.3.0` with build provenance via GitHub Actions (`pypa/gh-action-pypi-publish` with `attestations: true`)
