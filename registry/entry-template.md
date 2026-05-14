# Registry Entry — agience-flare-dkg-integration

This file is the source for the PR against [`OriginTrail/dkg-integrations`](https://github.com/OriginTrail/dkg-integrations).

Before filing the PR, fill in the two `TODO` values below (commit SHA and PyPI version after first publish).

---

## Integration metadata

- **Name:** Agience FLARE × DKG v10 Integration
- **Slug:** `agience-flare-dkg-integration`
- **Bounty tag:** `cfi-dkgv10-r1`
- **Category:** agent-memory / research-workflow / governance
- **Round:** DKG v10 Round 1 — Working Memory and Shared Memory
- **One-line summary:** Governance layer above DKG v10 — commit-gated Agience artifacts, policy-controlled projection, FLARE confidentiality, typed `agience:` RDF Knowledge Assets. Complementary to (not a replacement for) `dkg mcp setup`.
- **Primary interface:** DKG v10 MCP Streamable HTTP (`POST /mcp`) — `dkg-create` and `dkg-sparql-query` tools
- **Repository:** https://github.com/Muffinman75/agience-flare-dkg-integration
- **Package:** `agience-flare-dkg-integration` on PyPI
- **Package version:** `0.3.0`
- **Pinned commit SHA:** TODO — `5eb7e653dd48efd0c6ce8f7325c4a02285f51d1f`
- **License:** MIT
- **SPDX:** `MIT`
- **Maintainer:** Manoj Modhwadia — manojmodhwadia@outlook.com — [@Muffinman75](https://github.com/Muffinman75)

## Declared network egress

1. DKG node endpoint (`DKG_BASE_URL`, default `http://localhost:8081`) — always
2. FLARE service endpoint — only when `protected-search` mode is explicitly configured; disabled by default

## Declared write authority

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
| This repository | Integration bridge | MCP stdio server, MCP Streamable HTTP client, typed JSON-LD, CLI, governed-mode (`--from-agience-artifact`) gate, 60 unit tests + 5 integration tests |

## Compliance checklist

- [x] Package published to PyPI with build provenance (GitHub Actions `pypa/gh-action-pypi-publish` with `attestations: true`)
- [x] No `postinstall` or `preinstall` scripts
- [x] LICENSE file present, SPDX = `MIT`
- [x] Network egress declared above
- [x] Write authority declared above, Curator operations called out
- [x] No dynamic code loading, no `eval` on remote input
- [x] `pip audit --production` clean
- [x] Contributor attestation in `docs/maintainer-statement.md`
- [x] 172 total tests (60 integration pkg unit + 5 integration + 6 Agience Core DKG + 101 FLARE)
- [x] GitHub Actions CI (unit tests, dependency audit, build verification)
- [ ] Demo link — TODO: add after recording
- [x] Design brief link — `DESIGN_BRIEF.md` in repo root
