# Security Notes

## Credential model

All credentials are read from environment variables — never hardcoded or logged.

- `DKG_TOKEN` — bearer token for the DKG v10 node HTTP API
- `DKG_BASE_URL` — base URL for the DKG node (default: `http://localhost:8081`)

No Agience platform credentials are required by this package. FLARE service credentials are only used when `retrieval_profile = protected-search` is explicitly configured by the operator — this mode is not enabled by default.

## Declared network egress

All external domains contacted by this package:

1. **DKG node endpoint** — the `DKG_BASE_URL` value (default: `http://localhost:8081`). This is the only endpoint contacted in the default configuration.
2. **FLARE service endpoint** — only when the operator explicitly enables `protected-search` mode. Disabled by default. When enabled, only derived summary/claim projections are written to DKG; raw artifact content remains FLARE-protected.

No other external domains are contacted. No telemetry, no analytics endpoints, no remote module loading.

## Declared DKG write authority

Every DKG endpoint invoked by this package:

| Endpoint | Operation | Authority |
|---|---|---|
| `GET /api/agents` | Health check / token validation | Read-only |
| `POST /api/memory/turn` | Write Knowledge Asset to Working Memory | Write (WM) |
| `POST /api/assertion/:name/promote` | Promote WM assertion to Shared Memory | **Curator-authorized (SHARE)** |
| `POST /api/memory/search` | Search Working and/or Shared Memory | Read-only |

The SHARE operation (`/api/assertion/:name/promote`) is **always explicit and operator-initiated**. It is never called automatically, silently, or as a side effect of a write operation.

PUBLISH toward Verified Memory is not invoked in this Round 1 package.

## Curator authority stance

No SHARE or PUBLISH operation is invoked without explicit caller intent. The CLI `promote` command requires the operator to pass a `turnUri` and `context_graph_id` explicitly. There is no background promotion loop.

## Dynamic code loading

This package:
- does not fetch or execute remote code
- does not use `eval` on any external input
- does not import any internal DKG node packages (`@origintrail-official/dkg-core` or any non-public subpath)
- does not patch the DKG node daemon

## Package hygiene

- No `postinstall` or `preinstall` scripts
- MIT license, SPDX identifier `MIT`
- `pip audit --production` clean
- Dependencies pinned with lower bounds only (`httpx>=0.27`, `pydantic>=2.0,<3`, `typer>=0.12,<1`) for compatibility
- Build provenance published via GitHub Actions (`pip publish --provenance`)
