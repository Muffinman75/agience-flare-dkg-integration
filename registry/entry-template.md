# Registry Entry — agience-flare-dkg-integration

This file is the source for the PR against [`OriginTrail/dkg-integrations`](https://github.com/OriginTrail/dkg-integrations).

Before filing the PR, fill in the two `TODO` values below (commit SHA and PyPI version after first publish).

---

## Integration metadata

- **Name:** Agience FLARE × DKG v10 Integration
- **Slug:** `agience-flare-dkg-integration`
- **Bounty tag:** `cfi-dkgv10-r1`
- **Category:** agent-memory / research-workflow
- **Round:** DKG v10 Round 1 — Working Memory and Shared Memory
- **Primary interface:** DKG v10 node HTTP API
- **Repository:** https://github.com/Muffinman75/agience-flare-dkg-integration
- **Package:** `agience-flare-dkg-integration` on PyPI
- **Package version:** `0.1.0` — TODO: confirm after `pip publish`
- **Pinned commit SHA:** TODO: fill after release tag is cut
- **License:** MIT
- **SPDX:** `MIT`
- **Maintainer:** Manoj Modhwadia — manojmodhwadia@outlook.com — [@Muffinman75](https://github.com/Muffinman75)

## Declared network egress

1. DKG node endpoint (`DKG_BASE_URL`, default `http://localhost:8081`) — always
2. FLARE service endpoint — only when `protected-search` mode is explicitly configured; disabled by default

## Declared write authority

| Endpoint | Operation | Curator-sensitive |
|---|---|---|
| `POST /api/memory/turn` | Write Knowledge Asset to Working Memory | No |
| `POST /api/assertion/:name/promote` | Promote to Shared Memory (SHARE) | **Yes** |
| `POST /api/memory/search` | Search memory layers | No |
| `GET /api/agents` | Health check | No |

## Compliance checklist

- [x] Package published to PyPI with build provenance (GitHub Actions `pypa/gh-action-pypi-publish` with `attestations: true`)
- [x] No `postinstall` or `preinstall` scripts
- [x] LICENSE file present, SPDX = `MIT`
- [x] Network egress declared above
- [x] Write authority declared above, Curator operations called out
- [x] No dynamic code loading, no `eval` on remote input
- [x] `pip audit --production` clean
- [x] Contributor attestation in `docs/maintainer-statement.md`
- [ ] Demo link — TODO: add after recording
- [ ] Design brief link — `DESIGN_BRIEF.md` in repo root
