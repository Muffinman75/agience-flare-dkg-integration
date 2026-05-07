# agience-flare-dkg-integration

A **platform-level integration** bridging [Agience Core](https://github.com/Agience/agience-core) (governed MCP-native artifact platform), [FLARE](https://github.com/Agience/flare-index) (cryptographically enforced encrypted vector search), and OriginTrail DKG v10 Working Memory / Shared Memory into a three-layer trust gradient for collaborative knowledge production.

## Features

- **MCP stdio server** (`agience-dkg-mcp`) — exposes `agience_wm_write`, `agience_promote`, `agience_search` tools for Claude Desktop, Cursor, Claude Code, and any MCP host
- Writes committed Agience artifacts to DKG v10 **Working Memory** as typed JSON-LD Knowledge Assets with the `agience:` RDF vocabulary — SPARQL-queryable by type, author, collection, and memory layer
- Promotes eligible assets to **Shared Memory** (SHARE) via `dkg-create` (privacy=public)
- Searches across memory layers via `dkg-sparql-query` with typed predicates
- All DKG calls use **MCP Streamable HTTP** at `POST /mcp` with SSE stream handling
- Distinguishes MCP transport success from blockchain anchoring state (`status: anchored` vs `status: pending`)
- FLARE optional path: when `policy_class = "internal-confidential"`, only derived projections reach DKG; raw content stays encrypted

## Install

```bash
pip install agience-flare-dkg-integration
```

## MCP Server (Claude Desktop, Cursor, etc.)

Add to your MCP client config:

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

Tools: `agience_wm_write`, `agience_promote`, `agience_search`.

## CLI

```bash
export DKG_BASE_URL=http://localhost:8081
export DKG_TOKEN=your-bearer-token

# Write to Working Memory
agience-dkg wm-write \
  --title "Architecture Decision: use DKG v10" \
  --artifact-type decision \
  --artifact-id art-001 \
  --content "We will use DKG v10 Working Memory as the shared knowledge substrate." \
  --context-graph-id my-context-graph \
  --collection-id my-project

# Promote to Shared Memory (SHARE)
agience-dkg promote <turn-uri> --context-graph-id my-context-graph

# Search
agience-dkg search "architecture decisions" --context-graph-id my-context-graph
```

## Python API

```python
from agience_dkg_integration import DkgHttpClient, MemoryTurnRequest
from agience_dkg_integration.formatter import artifact_to_markdown, session_uri_for_collection

client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="token")

result = client.memory_turn(MemoryTurnRequest(
    contextGraphId="my-context-graph",
    markdown=artifact_to_markdown(title="My Note", content="...", artifact_type="research-note", artifact_id="art-001"),
    layer="wm",
    sessionUri=session_uri_for_collection("my-project"),
))
print(result.turn_uri)
```

## Links

- [Full documentation & design brief](https://github.com/Muffinman75/agience-flare-dkg-integration)
- [Agience Core](https://github.com/Agience/agience-core)
- [FLARE Index](https://github.com/Agience/flare-index) · [Paper](https://github.com/Agience/flare-index/blob/main/paper/flare.md)

## License

MIT
