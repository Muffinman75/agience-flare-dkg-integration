# Registry Entry — agience-flare-dkg-integration

This file is the source for the PR against [`OriginTrail/dkg-integrations`](https://github.com/OriginTrail/dkg-integrations).

Filed as PR against [`OriginTrail/dkg-integrations`](https://github.com/OriginTrail/dkg-integrations).

---

## Integration metadata

- **Name:** Agience FLARE × DKG v10 Integration
- **Slug:** `agience-flare-dkg-integration`
- **Bounty tag:** `cfi-dkgv10-r1`
- **Category:** agent-memory / research-workflow / governance
- **Round:** DKG v10 Round 1 — Working Memory and Shared Memory
- **One-line summary:** Governance layer above DKG v10 — commit-gated Agience artifacts, policy-controlled projection, FLARE confidentiality, typed `agience:` RDF Knowledge Assets. Speaks the local v10 daemon HTTP API and MCP Streamable HTTP.
- **Primary interface:** Local DKG v10 daemon HTTP API (`/api/assertion/*`, `/api/shared-memory/write`, `/api/assertion/{name}/promote`, `/api/query`) — bearer-token authenticated.
- **Secondary interface:** DKG v10 MCP Streamable HTTP (`POST /mcp`) — `dkg-create` and `dkg-sparql-query` tools (for MCP-fronted nodes such as those configured via `dkg mcp setup`).
- **Repository:** https://github.com/Muffinman75/agience-flare-dkg-integration
- **Package:** `agience-flare-dkg-integration` on PyPI
- **Package version:** `0.4.0`
- **Pinned commit SHA:** `6e3a7676fa4ef76bccf9ae47e6b3974a71c036f8` (v0.4.0 release commit)
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
| `POST /api/assertion/create` | Create assertion in Context Graph | No |
| `POST /api/assertion/{name}/write` | Write JSON-LD body | No |
| `POST /api/shared-memory/write` (`localOnly=true`) | Working Memory write | No |
| `POST /api/shared-memory/write` (`localOnly=false`) | Shared Memory write | **Yes** |
| `POST /api/assertion/{name}/promote` | SHARE Working → Shared | **Yes** |
| `POST /api/query` | SPARQL search | No |
| `GET /health` | Health check | No |

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
| [Agience Core](https://github.com/Agience/agience-core) | Governed MCP-native artifact platform | `backend/api/dkg_integration.py` (receipt schema, 233 lines), `backend/services/dkg_integration_service.py` (policy mapping, projection validation), 6 DKG service tests |
| [FLARE Index](https://github.com/Agience/flare-index) | Cryptographic vector search | 101-test suite, AES-256-GCM per-cell encryption, Shamir K-of-M threshold oracle, [research paper](https://github.com/Agience/flare-index/blob/main/paper/flare.md) |
| This repository | Integration bridge | MCP stdio server, daemon HTTP client + MCP Streamable HTTP client (selectable via `--transport`), typed JSON-LD, CLI, governed-mode (`--from-agience-artifact`) gate, 75 unit tests + 5 integration tests |

## Compliance checklist

- [x] Package published to PyPI with build provenance (GitHub Actions `pypa/gh-action-pypi-publish` with `attestations: true`)
- [x] No `postinstall` or `preinstall` scripts
- [x] LICENSE file present, SPDX = `MIT`
- [x] Network egress declared above
- [x] Write authority declared above, Curator operations called out
- [x] No dynamic code loading, no `eval` on remote input
- [x] `pip audit --production` clean
- [x] Contributor attestation in `docs/maintainer-statement.md`
- [x] 187 total tests (75 integration pkg unit + 5 integration + 6 Agience Core DKG + 101 FLARE)
- [x] GitHub Actions CI (unit tests, dependency audit, build verification)
- [x] Demo link — https://youtu.be/0Zm8R3vQzgU
- [x] Design brief link — `DESIGN_BRIEF.md` in repo root
