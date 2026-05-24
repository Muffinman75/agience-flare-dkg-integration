# Agience FLARE × DKG v10 Integration

**Bounty tag:** `cfi-dkgv10-r1` | **License:** MIT | **Package:** `agience-flare-dkg-integration`

**The governance layer above `dkg mcp setup`.** OriginTrail's official `dkg mcp setup` (shipped 7 May 2026) makes MCP-to-DKG a two-command commodity. **This integration is what sits upstream** — Agience Core for commit-gated authoring, FLARE for cryptographic confidentiality, and typed `agience:` RDF Knowledge Assets — so what reaches Working Memory is governed, attributable, and SPARQL-queryable, not raw LLM output.

See [`docs/vs-dkg-mcp-setup.md`](docs/vs-dkg-mcp-setup.md) for the head-to-head.

## The three-layer architecture

DKG v10 provides the shared memory substrate. But what gets written there matters: raw LLM outputs are noise; governed, typed, attributed Knowledge Assets are signal. And when the source material is sensitive, a confidentiality boundary determines what reaches the shared layer.

- **Agience Core** — governed authoring: typed artifacts, versioned collections, human-review commit gates, provenance receipts, 11-tool MCP server, 8 agent persona servers. DKG receipt schemas and policy routing are built directly into the platform.
- **FLARE** — confidential retrieval: AES-256-GCM encrypted vector search with Shamir K-of-M threshold oracle, Ed25519 signed grant ledger, light-cone graph authorization. 101 tests, 95.6% recall vs plaintext FAISS.
- **DKG v10** — open verifiable memory: Working Memory → Shared Memory → Verified Memory.

## What this package does

- **MCP stdio server** (`agience-dkg-mcp`) — exposes `agience_wm_write`, `agience_promote`, `agience_search` tools for Claude Desktop, Cursor, Claude Code, and any MCP host
- Writes committed Agience artifacts to DKG v10 **Working Memory** as typed JSON-LD Knowledge Assets with the `agience:` RDF vocabulary — SPARQL-queryable by type, author, collection, and memory layer
- Promotes eligible assets to **Shared Memory** (SHARE) via `dkg-create` (privacy=public)
- Searches across memory layers via `dkg-sparql-query` with typed predicates
- All DKG calls use **MCP Streamable HTTP** at `POST /mcp` with SSE stream handling
- Groups all artifacts under a stable `sessionUri` for oracle-queryable Context Graph scoping
- Distinguishes MCP transport success from blockchain anchoring state (`status: anchored` vs `status: pending`)
- FLARE optional path: when `policy_class = "internal-confidential"`, only derived projections reach DKG; raw content stays encrypted

## What makes this different

| | Typical DKG integration | This submission |
|---|---|---|
| **What gets written** | Raw content or unstructured payloads | Governed, committed, typed artifacts that pass a five-dimension policy evaluation before reaching DKG |
| **Who decides what reaches DKG** | The calling code | A `PolicyMappingRecord` with policy class, promotion profile, export profile, retrieval profile, and identity profile — evaluated at commit time |
| **Sensitive content** | Omitted or manually redacted | Physically encrypted by FLARE (AES-256-GCM per-cell, Shamir threshold oracle key issuance); only derived projections reach DKG |
| **Knowledge Asset structure** | Generic `schema:Article` or flat JSON | Typed `agience:` RDF vocabulary with 8+ SPARQL-queryable predicates across Context Graphs |
| **Provenance** | None or ad-hoc | Seven receipt types (commit, grant, revoke, access, projection, publication, provenance) generated on every commit |
| **Test coverage** | Package-level tests | 172 tests across 4 suites: integration package (60 unit + 5 integration), Agience Core DKG service (6), FLARE (101) |

## Install

One-line install (recommended — installs the `agience-dkg` CLI globally in an isolated venv):

```bash
pipx install agience-flare-dkg-integration
```

Or via pip:

```bash
python -m pip install --user agience-flare-dkg-integration
```

> An npm wrapper of the same name is also published for ecosystem familiarity; see [`npm-wrapper/README.md`](npm-wrapper/README.md). The wrapper delegates to the Python CLI above — `pipx` is the canonical one-line install.

## MCP Server (for Claude Desktop, Cursor, etc.)

Add to your MCP client config (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "agience-dkg": {
      "command": "agience-dkg-mcp",
      "env": {
        "DKG_BASE_URL": "http://localhost:8081",
        "DKG_TOKEN": "your-bearer-token"
      }
    }
  }
}
```

This exposes three tools: `agience_wm_write`, `agience_promote`, `agience_search`.

## CLI Quick start

```bash
# 1) Install the official DKG v10 daemon (one-time)
npm install -g @origintrail-official/dkg
dkg init                       # writes ~/.dkg/auth.token
DKG_PORT=9201 dkg start        # 9201 avoids the Windows Elasticsearch :9200 collision

# 2) Copy the env template and edit (sane daemon defaults are already in there)
cp integration/package/.env.example integration/package/.env

# 3) Write a Knowledge Asset to Working Memory
agience-dkg wm-write \
  --title "Architecture Decision: use DKG v10" \
  --artifact-type Decision \
  --artifact-id art-001 \
  --content "We will use DKG v10 Working Memory as the shared knowledge substrate." \
  --context-graph-id agience-demo \
  --collection-id my-project \
  --author "Manoj" \
  --tags "architecture,dkg-v10"

agience-dkg promote <turnUri-from-above> --context-graph-id agience-demo
agience-dkg search "architecture decisions" --context-graph-id agience-demo
```

The default transport is **daemon** — direct HTTP to your local DKG v10 daemon at `http://127.0.0.1:9201`. The bearer token is auto-read from `~/.dkg/auth.token`, so you don't have to set one. WM writes do **not** require an on-chain publish, so the demo runs fully local — no TRAC staking, no testnet RPC.

### Governed mode (drafts can't reach DKG)

Add `--from-agience-artifact <id>` to fetch a committed artifact from an Agience instance and refuse to project it unless its state is `committed`. Title, type, content, tags, and the `commit_receipt_id` are populated automatically:

```bash
agience-dkg wm-write \
  --from-agience-artifact 9667ca6d-cc37-410f-944d-84b838fb46d0 \
  --title "ADR: DKG v10 as Verifiable Memory Substrate" \
  --artifact-type decision \
  --context-graph-id agience-demo
```

### Alternative transport — MCP Streamable HTTP

Speaks to a DKG node's `/mcp` endpoint (e.g. `dkg-node/apps/agent` or a node fronted by `dkg mcp setup`). Set `DKG_TRANSPORT=mcp`, `DKG_BASE_URL=http://localhost:8083`, and `DKG_TOKEN=<mcp-bearer>` in your `.env`, or pass `--transport mcp --base-url ... --token ...` per command.

> **WSL2 + Windows Agience tip:** if the integration runs in WSL but the Agience backend runs on Windows, `localhost` will not reach it. Use the Windows host IP: `AGIENCE_BASE_URL=http://$(ip route show | awk '/default/ {print $3}'):8081`. The CLI prints this hint automatically on connection refused.

## Python API

```python
from agience_dkg_integration import DkgHttpClient, MemoryTurnRequest
from agience_dkg_integration.formatter import artifact_to_markdown, session_uri_for_collection

client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="token")

markdown = artifact_to_markdown(
    title="My Research Note",
    artifact_type="research-note",
    artifact_id="art-001",
    content="...",
    author="Manoj",
    tags=["dkg-v10"],
    collection_id="my-project",
)

result = client.memory_turn(MemoryTurnRequest(
    contextGraphId="my-context-graph",
    markdown=markdown,
    layer="wm",
    sessionUri=session_uri_for_collection("my-project"),
))
print(result.turn_uri)
```

## Repository layout

```
package/                Python package source (agience_dkg_integration)
  src/
    agience_dkg_integration/
      mcp_server.py     MCP stdio server (agience-dkg-mcp entry point)
      client.py         DkgHttpClient — MCP Streamable HTTP transport (legacy)
      daemon_client.py  DkgDaemonClient — direct HTTP to local DKG v10 daemon
      models.py         Pydantic request/response models with artifact metadata
      formatter.py      artifact_to_markdown, session_uri_for_collection
      cli.py            agience-dkg CLI (wm-write, promote, search; --transport switch)
  tests/
    unit/               75 unit tests (governance gate, both transports, MCP server, JSON-LD, models)
    integration/        5 live-node integration tests
docs/
  security-notes.md
  maintainer-statement.md
  demo-script.md
registry/
  entry-template.md     PR payload for OriginTrail/dkg-integrations
DESIGN_BRIEF.md         Full submission design brief
LICENSE                 MIT
```

**Parent platform repositories** (DKG models and FLARE integration are part of the same body of work):
- [Agience Core](https://github.com/Agience/agience-core) — `backend/api/dkg_integration.py` (receipt schemas), `backend/services/dkg_integration_service.py` (policy mapping, projection validation), 6 DKG service tests
- [FLARE Index](https://github.com/Agience/flare-index) — 101-test encrypted vector search, [research paper](https://github.com/Agience/flare-index/blob/main/paper/flare.md)

## Test coverage

| Suite | Count | Requires DKG node |
|---|---|---|
| Integration package unit tests | 75 | No |
| Integration package integration tests | 5 | Yes |
| Agience Core DKG service tests | 6 | No |
| FLARE test suite | 101 | No (Docker only) |

```bash
# Unit tests (no DKG node required)
pytest package/tests/unit -v

# Integration tests (requires a local DKG v10 node)
DKG_BASE_URL=http://localhost:8081 DKG_TOKEN=<token> DKG_CONTEXT_GRAPH=<id> \
pytest package/tests/integration -v
```

## Design brief

See [DESIGN_BRIEF.md](DESIGN_BRIEF.md) for the full submission brief covering the three-layer architecture (Agience Core + FLARE + DKG), platform-level DKG models, receipt schema, policy mapping, promotion path, oracle-readiness, and security notes.

## Maintainer

Manoj Modhwadia ([@Muffinman75](https://github.com/Muffinman75)) — manojmodhwadia@outlook.com  
6-month support commitment from registry acceptance.
