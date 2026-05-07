# Agience FLARE × DKG v10 Integration

**Bounty tag:** `cfi-dkgv10-r1` | **License:** MIT | **Package:** `agience-flare-dkg-integration`

A **platform-level integration** bridging [Agience Core](https://github.com/Agience/agience-core) (governed MCP-native artifact platform), [FLARE](https://github.com/Agience/flare-index) (cryptographically enforced encrypted vector search — [paper](https://github.com/Agience/flare-index/blob/main/paper/flare.md)), and DKG v10 Working Memory / Shared Memory into a three-layer trust gradient for collaborative knowledge production.

## Why three layers matter

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

## Install

```bash
pip install agience-flare-dkg-integration
```

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
export DKG_BASE_URL=http://localhost:8081
export DKG_TOKEN=your-bearer-token

# Write an artifact to Working Memory
agience-dkg wm-write \
  --title "Architecture Decision: use DKG v10" \
  --artifact-type decision \
  --artifact-id art-001 \
  --content "We will use DKG v10 Working Memory as the shared knowledge substrate." \
  --context-graph-id <your-context-graph-id> \
  --collection-id my-project \
  --author "Manoj" \
  --tags "architecture,dkg-v10"

# Promote to Shared Memory (SHARE)
agience-dkg promote <turnUri-from-above> --context-graph-id <id>

# Search
agience-dkg search "architecture decisions" --context-graph-id <id>
```

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
      client.py         DkgHttpClient — MCP Streamable HTTP to DKG node
      models.py         Pydantic request/response models with artifact metadata
      formatter.py      artifact_to_markdown, session_uri_for_collection
      cli.py            agience-dkg CLI (wm-write, promote, search)
  tests/
    unit/               43 unit tests (MCP server, JSON-LD, error handling, models)
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
| Integration package unit tests | 43 | No |
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
