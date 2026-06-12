# Maintainer Statement

## Maintainer

- **Name:** Manoj Modhwadia
- **GitHub:** [@Muffinman75](https://github.com/Muffinman75)
- **Email:** manojmodhwadia@outlook.com
- **Repository:** https://github.com/Muffinman75/agience-flare-dkg-integration

## Support commitment

6-month support window from the date of registry acceptance.

Commitment includes:
- Issue triage within 5 business days
- Compatibility fixes when supported DKG v10 public interfaces change
- Semantic versioning — breaking changes are major version bumps with migration notes
- Response to security disclosures within 48 hours

## Scope

The maintained surface is the DKG v10 public interface set declared in bounty § 5:

**Daemon HTTP API (default transport — DKG `v10.0.0-rc.17` unified `/api/knowledge-assets` surface, OT-RFC-43):**
- `POST /api/knowledge-assets` + `POST /api/knowledge-assets/{name}/wm/write` (Working Memory write)
- `POST /api/shared-memory/write` (Shared Memory write)
- `POST /api/knowledge-assets/{name}/swm/share` (Curator-authorized SHARE; rc.17 rename of `promote`)
- `POST /api/knowledge-assets/{name}/vm/publish` (Curator-authorized PUBLISH — Verifiable Memory, on-chain)
- `POST /api/query` (memory search)
- `GET /api/status` (health probe)

_Legacy `/api/assertion/*` routes are supported via a transparent one-time `404` fallback for pre-rc.17 daemons._

**MCP Streamable HTTP (alternative transport):**
- `POST /mcp` → `dkg-create` tool (Working Memory write and Shared Memory promotion)
- `POST /mcp` → `dkg-sparql-query` tool (memory search)
- `GET /health` (health check)

No guarantee of compatibility beyond these public interfaces if DKG internal packages change.

## Contributor attestation

The code in this repository is my own original work, written for the purpose of this integration. It is properly licensed under MIT. It contains no intentional backdoors, malicious code, or undeclared network behaviour. All external network contacts are declared in the security notes.
