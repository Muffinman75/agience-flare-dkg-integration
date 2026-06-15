# Registry Entry — agience-flare-dkg-integration

This file is the source for the PR against [`OriginTrail/dkg-integrations`](https://github.com/OriginTrail/dkg-integrations).

Filed as PR against [`OriginTrail/dkg-integrations`](https://github.com/OriginTrail/dkg-integrations).

---

## Integration metadata

- **Name:** Agience FLARE × DKG v10 Integration
- **Slug:** `agience-flare-dkg-integration`
- **Bounty tag:** `cfi-dkgv10-r1`
- **Category:** agent-memory / research-workflow / governance
- **Round:** DKG v10 Round 1 — Working Memory and Shared Memory (Verifiable Memory publish path included for rc.17)
- **One-line summary:** Governance layer above DKG v10 — commit-gated Agience artifacts, policy-controlled projection, FLARE confidentiality, typed `agience:` RDF Knowledge Assets. Speaks the rc.17 local v10 daemon HTTP API and MCP Streamable HTTP.
- **Primary interface:** Local DKG v10 daemon HTTP API — rc.17 unified `/api/knowledge-assets` surface (`POST /api/knowledge-assets`, `/wm/write`, `/swm/share`, `/vm/publish`), plus `/api/shared-memory/write` and `/api/query` — bearer-token authenticated. Transparent one-time `404` fallback to the legacy `/api/assertion/*` routes for pre-rc.17 daemons.
- **DKG version tested:** `v10.0.0-rc.17` (also compatible with rc.16 via fallback).
- **Secondary interface:** DKG v10 MCP Streamable HTTP (`POST /mcp`) — `dkg-create` and `dkg-sparql-query` tools (for MCP-fronted nodes such as those configured via `dkg mcp setup`).
- **Repository:** https://github.com/Muffinman75/agience-flare-dkg-integration
- **Package:** `agience-flare-dkg-integration` on PyPI
- **Package version:** `0.4.1`
- **Pinned commit SHA:** `6fdb51c7e3a42021888b780cf95e787b05cf8207` (v0.4.1 release commit)
- **License:** MIT
- **SPDX:** `MIT`
- **Maintainer:** Manoj Modhwadia — manojmodhwadia@outlook.com — [@Muffinman75](https://github.com/Muffinman75)

## Declared network egress

1. DKG endpoint (`DKG_BASE_URL`) — daemon default `http://127.0.0.1:9201`, MCP default `http://localhost:8083` — always.
2. Agience platform endpoint (`AGIENCE_BASE_URL`) — only when `--from-agience-artifact` is used to fetch a governed artifact before projection.
3. FLARE service endpoint — only when `protected-search` mode is explicitly configured; disabled by default.

## Declared write authority

### Daemon HTTP API (canonical)

| Endpoint | Operation | Curator-sensitive |
|---|---|---|
| `POST /api/knowledge-assets` | Create KA + open WM draft (atomic create+write) | No |
| `POST /api/knowledge-assets/{name}/wm/write` | Append quads to the WM draft | No |
| `POST /api/shared-memory/write` (`localOnly=true`) | Working Memory write (direct SWM path) | No |
| `POST /api/shared-memory/write` (`localOnly=false`) | Shared Memory write | **Yes** |
| `POST /api/knowledge-assets/{name}/swm/share` | SHARE Working → Shared (rc.17 rename of `promote`) | **Yes** |
| `POST /api/knowledge-assets/{name}/vm/publish` | Publish to Verifiable Memory (on-chain) | **Yes** |
| `POST /api/query` | SPARQL search | No |
| `GET /api/status` / `GET /health` | Health check | No |

_Legacy fallback (pre-rc.17 daemons only, auto-detected on `404`): `POST /api/assertion/create`, `POST /api/assertion/{name}/write`, `POST /api/assertion/{name}/promote`._

### MCP Streamable HTTP (secondary)

| Endpoint / Tool | Operation | Curator-sensitive |
|---|---|---|
| `POST /mcp` → `dkg-create` (privacy=private) | Write Knowledge Asset to Working Memory | No |
| `POST /mcp` → `dkg-create` (privacy=public) | Promote to Shared Memory (SHARE) | **Yes** |
| `POST /mcp` → `dkg-sparql-query` | Search memory layers | No |
| `GET /health` | Health check | No |

## Parent platform repositories

This integration is part of a larger body of work spanning three repositories:

| Repository | Role | Key DKG-relevant components |
|---|---|---|
| [Agience Core](https://github.com/Agience/agience-core) | Governed MCP-native artifact platform | `backend/api/dkg_integration.py` (receipt schema), `backend/services/dkg_integration_service.py` (policy mapping, projection validation + DKG projection read model), `frontend/src/components/workspace/DkgProjectionPanel.tsx` (DKG projection panel), DKG service tests |
| [FLARE Index](https://github.com/Agience/flare-index) | Cryptographic vector search | 101-test suite, AES-256-GCM per-cell encryption, Shamir K-of-M threshold oracle, [research paper](https://github.com/Agience/flare-index/blob/main/paper/flare.md) |
| This repository | Integration bridge | MCP stdio server, daemon HTTP client (rc.17 KA surface + legacy fallback) + MCP Streamable HTTP client (selectable via `--transport`), typed JSON-LD, CLI (`wm-write`/`promote`/`vm-publish`/`search`), governed-mode (`--from-agience-artifact`) gate, 82 unit tests + 5 integration tests |

> **Fork note.** The `agience-core` and `flare-index` changes for this integration live on the author's forks ([github.com/Muffinman75](https://github.com/Muffinman75)), not the upstream `Agience/*` repos.

## Compliance checklist

- [x] Package published to PyPI with build provenance (GitHub Actions `pypa/gh-action-pypi-publish` with `attestations: true`)
- [x] No `postinstall` or `preinstall` scripts
- [x] LICENSE file present, SPDX = `MIT`
- [x] Network egress declared above
- [x] Write authority declared above, Curator operations called out
- [x] No dynamic code loading, no `eval` on remote input
- [x] `pip audit --production` clean
- [x] Contributor attestation in `docs/maintainer-statement.md`
- [x] 194 total tests (82 integration pkg unit + 5 integration + 6+ Agience Core DKG + 101 FLARE)
- [x] GitHub Actions CI (unit tests, dependency audit, build verification)
- [x] Demo link — https://youtu.be/0Zm8R3vQzgU
- [x] Design brief link — `DESIGN_BRIEF.md` in repo root
