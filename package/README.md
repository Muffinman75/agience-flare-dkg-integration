# agience-flare-dkg-integration

**The governance layer above `dkg mcp setup`.** OriginTrail's official `dkg mcp setup` (shipped 7 May 2026) makes MCP-to-DKG a two-command commodity. **This package is what sits upstream** — committed [Agience Core](https://github.com/Agience/agience-core) artifacts, optional [FLARE](https://github.com/Agience/flare-index) confidentiality, and typed `agience:` RDF Knowledge Assets — so what reaches Working Memory is governed, attributable, and SPARQL-queryable, not raw LLM output.

See the [head-to-head comparison](https://github.com/Muffinman75/agience-flare-dkg-integration/blob/main/docs/vs-dkg-mcp-setup.md) and [design brief](https://github.com/Muffinman75/agience-flare-dkg-integration/blob/main/DESIGN_BRIEF.md).

## Features

- **MCP stdio server** (`agience-dkg-mcp`) — exposes `agience_wm_write`, `agience_share` (`agience_promote` alias), `agience_search` tools for Claude Desktop, Cursor, Claude Code, and any MCP host
- Writes committed Agience artifacts to DKG v10 **Working Memory** as typed JSON-LD Knowledge Assets with the `agience:` RDF vocabulary — SPARQL-queryable by type, author, collection, and memory layer
- Promotes eligible assets to **Shared Memory** (SHARE) via the daemon's `POST /api/knowledge-assets/{name}/swm/share` (or `dkg-create` with `privacy=public` on MCP transport)
- Searches across memory layers via the daemon's `POST /api/query` (or `dkg-sparql-query` on MCP transport)
- **Default transport:** direct HTTP to the local DKG v10 daemon at `http://127.0.0.1:9201`; bearer token auto-read from `~/.dkg/auth.token`. **Alternative transport:** MCP Streamable HTTP at `POST /mcp` with SSE stream handling
- Distinguishes transport success from blockchain anchoring state (`status: anchored` vs `status: pending`)
- FLARE optional path: when `policy_class = "internal-confidential"`, only derived projections reach DKG; raw content stays encrypted

## Install

```bash
pip install agience-flare-dkg-integration
```

## MCP Server (Claude Desktop, Cursor, etc.)

Default config uses the local DKG v10 daemon — no token is needed because the daemon transport auto-reads `~/.dkg/auth.token`:

```json
{
  "mcpServers": {
    "agience-dkg": {
      "command": "agience-dkg-mcp",
      "env": {
        "DKG_BASE_URL": "http://127.0.0.1:9201"
      }
    }
  }
}
```

Tools: `agience_wm_write`, `agience_share` (`agience_promote` alias), `agience_search`.

To target an MCP-fronted DKG node instead, add `"DKG_TRANSPORT": "mcp"`, set `"DKG_BASE_URL": "http://localhost:8083"`, and add `"DKG_TOKEN": "<mcp-bearer>"`.

## CLI

```bash
# Default: local DKG v10 daemon. Bearer token auto-read from ~/.dkg/auth.token.
# DKG_BASE_URL defaults to http://127.0.0.1:9201 if unset.

# Write to Working Memory
agience-dkg wm-write \
  --title "Architecture Decision: use DKG v10" \
  --artifact-type decision \
  --artifact-id art-001 \
  --content "We will use DKG v10 Working Memory as the shared knowledge substrate." \
  --context-graph-id agience-demo \
  --collection-id my-project

# Share to Shared Memory (SHARE)
# Pass the Knowledge Asset NAME from the wm-write output (e.g. "art-001-Architecture-Decision-..."),
# NOT the v10.0.1 turnUri (its trailing revision index does not contain the KA name).
agience-dkg share <ka-name> --context-graph-id agience-demo
# agience-dkg promote is still accepted as a backward-compatible alias.

# Search
agience-dkg search "architecture decisions" --context-graph-id agience-demo
```

> **Resolved invocation block.** Every `wm-write` call prints a `# agience-dkg wm-write — resolved invocation (copy to replay):` block to stdout before the HTTP call fires, showing all fully-resolved flags with tokens truncated to 8 chars. Useful for testers and reviewers to copy and replay the exact command.

For MCP-fronted DKG nodes, add `--transport mcp --base-url http://localhost:8083 --token <mcp-bearer>`.

## Python API

```python
from agience_dkg_integration import DkgDaemonClient, MemoryTurnRequest
from agience_dkg_integration.formatter import artifact_to_markdown, session_uri_for_collection

# Default: local DKG v10 daemon. Bearer token auto-resolves from ~/.dkg/auth.token.
client = DkgDaemonClient(base_url="http://127.0.0.1:9201")

# Alternative: MCP-fronted DKG node
# from agience_dkg_integration import DkgHttpClient
# client = DkgHttpClient(base_url="http://localhost:8083", bearer_token="<mcp-bearer>")

result = client.memory_turn(MemoryTurnRequest(
    contextGraphId="agience-demo",
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
