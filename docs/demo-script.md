# Demo Script — Agience FLARE × DKG v10 Integration

## Goal

Produce a walkthrough for the Flagship Round 1 submission showing the **three-layer trust gradient**: Agience Core (governed authoring with native DKG models) → FLARE (cryptographic retrieval boundary) → DKG v10 (shared verifiable memory). The demo must cover:

- The platform-level DKG models in Agience Core
- The integration package: CLI, MCP server, typed JSON-LD
- Working Memory write, Shared Memory promotion, search
- Full test suite (unit + integration)
- FLARE reference and confidential retrieval path

## Services required

| Service | Start command | URL |
|---|---|---|
| DKG v10 agent node | `node dist/index.js` (in `dkg-node/apps/agent`) | `http://localhost:8081` |

Environment variables needed:
```bash
export DKG_BASE_URL=http://localhost:8081
export DKG_TOKEN=<bearer-token>
export DKG_CONTEXT_GRAPH=agience-demo
```

---

## Scene 1: The three-layer architecture (narration + slides)

Open the DESIGN_BRIEF.md and show the three-layer data flow diagram. Narrate:

> "This isn't a thin wrapper around a DKG API call. It's a platform-level integration across three systems. Agience Core provides governed authoring — every artifact is typed, versioned, and committed through a human-review gate. FLARE provides a cryptographic confidentiality boundary when the source material is sensitive. And DKG v10 provides the shared, verifiable memory substrate."

Show the key code files in Agience Core:

```bash
# Show the DKG receipt schema (165 lines of Pydantic models)
head -60 ../agience-core/backend/api/dkg_integration.py

# Show the policy mapping and projection validation
head -40 ../agience-core/backend/services/dkg_integration_service.py

# Show that workspace_service calls build_commit_receipt on every commit
grep -n "build_commit_receipt\|dkg_integration" ../agience-core/backend/services/workspace_service.py
```

Narrate: "Every Agience commit already generates a DKG-compatible receipt with actor, authority, and artifact references. The policy model evaluates what content reaches DKG — and FLARE mediates the retrieval path when content is classified as confidential."

---

## Scene 2: DKG node is running

```bash
curl http://localhost:8081/health
# → {"status":"ok","version":"..."}
```

---

## Scene 3: Write an artifact to Working Memory

```bash
agience-dkg wm-write \
  --title "Architecture Decision: DKG v10 as shared memory substrate" \
  --artifact-type decision \
  --artifact-id demo-001 \
  --content "We will use DKG v10 Working Memory as the shared knowledge substrate for agent collaboration. This enables multi-agent read/write access to a verifiable, open knowledge graph." \
  --context-graph-id agience-demo \
  --collection-id agience-architecture \
  --author "Manoj Modhwadia" \
  --tags "architecture,dkg-v10,working-memory"
```

Expected output: JSON with `turn_uri` (UAL), `status` (anchored or pending), and `layer` (wm).

Narrate: "The Knowledge Asset is typed JSON-LD with the `agience:` RDF vocabulary — not a generic `schema:Article`. It has a `@type` of `agience:decision`, predicates like `agience:author`, `agience:tags`, `agience:collection`, and `agience:memoryLayer`. This makes it SPARQL-queryable by type across Context Graphs."

If `status: pending`: "The MCP transport succeeded — the DKG node accepted the Knowledge Asset. Blockchain anchoring is pending because the testnet RPC is temporarily unavailable. The integration clearly distinguishes transport success from anchoring state."

---

## Scene 4: Promote to Shared Memory (SHARE)

```bash
agience-dkg promote <turn_uri_from_above> --context-graph-id agience-demo
```

Expected output: JSON confirming the promotion (SHARE operation via `dkg-create` with `privacy=public`).

Narrate: "This is a Curator-authorized operation. Nothing is promoted automatically — the operator explicitly calls promote with the UAL from the Working Memory write."

---

## Scene 5: Search memory

```bash
agience-dkg search "architecture decisions DKG working memory" --context-graph-id agience-demo
```

Expected output: SPARQL query results using `agience:` predicates.

---

## Scene 6: MCP server (agent integration)

```bash
# Show the MCP server starts cleanly
agience-dkg-mcp &
# → "agience-dkg MCP server running on stdio"
kill %1
```

Show the Claude Desktop / Cursor config:

```json
{
  "mcpServers": {
    "agience-dkg": {
      "command": "agience-dkg-mcp",
      "env": {
        "DKG_BASE_URL": "http://localhost:8081",
        "DKG_TOKEN": "<token>"
      }
    }
  }
}
```

Narrate: "Any MCP-capable agent — Claude Desktop, Cursor, Claude Code — can add this config and immediately use `agience_wm_write`, `agience_promote`, `agience_search` tools. Combined with Agience Core's 11-tool MCP server, agents can curate knowledge and write to DKG memory in a single workflow."

---

## Scene 7: Run the full test suite

```bash
# Unit tests (60 tests, no live node needed)
pytest package/tests/unit -v

# Integration tests (requires live DKG node)
DKG_BASE_URL=http://localhost:8081 \
DKG_TOKEN=<token> \
DKG_CONTEXT_GRAPH=agience-test \
pytest package/tests/integration -v
```

Expected output: `60 passed` (unit) + `5 passed` (integration).

Narrate: "60 unit tests cover the MCP server tool definitions and message routing, typed JSON-LD generation with the agience vocabulary, error status detection for blockchain failures, client operations, Pydantic models, the formatter, the Agience client governance gate (only `committed` artifacts may be projected), and the governed CLI flow. 5 integration tests run end-to-end against the live DKG node."

---

## Scene 8: FLARE reference (optional — show tests)

```bash
# Show FLARE's 101-test suite (runs in Docker)
cd ../flare-index && make test
```

Narrate: "FLARE provides the cryptographic confidentiality boundary. When an Agience collection is classified as `internal-confidential`, only derived projections reach DKG — raw content stays AES-256-GCM encrypted with per-cell keys issued by a Shamir threshold oracle. The integration's policy model routes retrieval through FLARE when needed."

---

## Recording checklist

- [ ] screen capture is readable
- [ ] three-layer architecture is explained (Agience Core → FLARE → DKG)
- [ ] Agience Core's DKG receipt schema and policy model are shown
- [ ] Working Memory and Shared Memory are explained using correct v10 terminology
- [ ] MCP transport (`POST /mcp`) is mentioned
- [ ] MCP server (`agience-dkg-mcp`) is shown with Claude Desktop config
- [ ] typed `agience:` JSON-LD vocabulary is shown and explained
- [ ] `turn_uri` from wm-write is shown being passed to promote
- [ ] blockchain anchoring state (`status: anchored` vs `pending`) is addressed
- [ ] unit test run shows 60 passed
- [ ] integration test run shows 5 passed
- [ ] FLARE is referenced (test suite or paper)
- [ ] no competitor submissions are mentioned
- [ ] services and env vars are listed

## Transport notes (for narration)

All DKG calls use the **MCP Streamable HTTP transport**:
- `POST /mcp` initialises an MCP session (JSON-RPC `initialize`)
- `POST /mcp` calls `dkg-create` or `dkg-sparql-query` as MCP tools
- Tool call responses stream back as SSE (`text/event-stream`); the client reads the first `data:` event
- Working Memory write = `dkg-create` with `privacy: "private"`
- Shared Memory promotion (SHARE) = `dkg-create` with `privacy: "public"`
- Search = `dkg-sparql-query` with a SPARQL SELECT query
