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

**Daemon HTTP API (default transport):**
- `POST /api/assertion/create` + `POST /api/assertion/{name}/write` (Working Memory write)
- `POST /api/shared-memory/write` (Shared Memory write)
- `POST /api/assertion/{name}/promote` (Curator-authorized SHARE)
- `POST /api/query` (memory search)
- `GET /api/status` (health probe)

**MCP Streamable HTTP (alternative transport):**
- `POST /mcp` → `dkg-create` tool (Working Memory write and Shared Memory promotion)
- `POST /mcp` → `dkg-sparql-query` tool (memory search)
- `GET /health` (health check)

No guarantee of compatibility beyond these public interfaces if DKG internal packages change.

## Contributor attestation

The code in this repository is my own original work, written for the purpose of this integration. It is properly licensed under MIT. It contains no intentional backdoors, malicious code, or undeclared network behaviour. All external network contacts are declared in the security notes.
