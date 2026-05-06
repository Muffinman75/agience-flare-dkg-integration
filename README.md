# Agience FLARE × DKG v10 Integration

**Bounty tag:** `cfi-dkgv10-r1` | **License:** MIT | **Package:** `agience-flare-dkg-integration`

Bridges [Agience](https://github.com/Agience/agience-core) — a governed MCP-native artifact platform — and [FLARE](https://github.com/Agience/flare-index/blob/main/paper/flare.md) (encrypted vector index with confidential retrieval) into DKG v10 **Working Memory** and **Shared Memory**, implementing the LLM-Wiki / autoresearch collaborative knowledge substrate.

## What it does

- Writes committed Agience artifacts (decisions, research notes, claims) to DKG v10 **Working Memory** as Knowledge Assets via `POST /api/memory/turn`
- Promotes eligible Working Memory assets to **Shared Memory** (SHARE) via `POST /api/assertion/:name/promote`
- Searches across Working Memory and Shared Memory via `POST /api/memory/search`
- Formats artifacts as structured Markdown with consistent RDF-extractable field headers
- Groups all artifacts for an Agience collection under a stable `sessionUri` for oracle-queryable Context Graph scoping

FLARE optional path: when `protected-search` mode is enabled, only derived summary/claim projections are written to DKG; raw artifact content stays FLARE-encrypted.

## Install

```bash
pip install agience-flare-dkg-integration
```

## Quick start

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
package/          Python package source (agience_dkg_integration)
  src/
    agience_dkg_integration/
      client.py     DkgHttpClient — memory_turn, assertion_promote, memory_search
      models.py     Pydantic request/response models
      formatter.py  artifact_to_markdown, session_uri_for_collection
      cli.py        agience-dkg CLI (wm-write, promote, search)
  tests/
    unit/           19 unit tests (no live node required)
    integration/    Live-node integration tests (skipped without env vars)
docs/
  security-notes.md
  maintainer-statement.md
  demo-script.md
registry/
  entry-template.md   PR payload for OriginTrail/dkg-integrations
DESIGN_BRIEF.md       Full submission design brief
LICENSE               MIT
```

## Running tests

```bash
# Unit tests (no DKG node required)
pytest package/tests/unit -v

# Integration tests (requires a local DKG v10 node)
DKG_BASE_URL=http://localhost:8081 DKG_TOKEN=<token> DKG_CONTEXT_GRAPH=<id> \
pytest package/tests/integration -v
```

## Design brief

See [DESIGN_BRIEF.md](DESIGN_BRIEF.md) for the full submission brief covering problem, architecture, memory layer mapping, promotion path, oracle-readiness, and security notes.

## Maintainer

Manoj Modhwadia ([@Muffinman75](https://github.com/Muffinman75)) — manojmodhwadia@outlook.com  
6-month support commitment from registry acceptance.
