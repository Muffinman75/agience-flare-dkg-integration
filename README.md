# Agience FLARE × DKG v10 Integration

**Bounty tag:** `cfi-dkgv10-r1` | **License:** MIT | **Package:** `agience-flare-dkg-integration`

**The governance layer above `dkg mcp setup`.** OriginTrail's official `dkg mcp setup` (shipped 7 May 2026) makes MCP-to-DKG a two-command commodity. **This integration is what sits upstream** — Agience Core for commit-gated authoring, FLARE for cryptographic confidentiality, and typed `agience:` RDF Knowledge Assets — so what reaches Working Memory is governed, attributable, and SPARQL-queryable, not raw LLM output.

See [`docs/vs-dkg-mcp-setup.md`](docs/vs-dkg-mcp-setup.md) for the head-to-head.

## The three-layer architecture

DKG v10 provides the shared memory substrate. But what gets written there matters: raw LLM outputs are noise; governed, typed, attributed Knowledge Assets are signal. And when the source material is sensitive, a confidentiality boundary determines what reaches the shared layer.

- **Agience Core** — governed authoring: typed artifacts (a first-class `content_type` media-type taxonomy), versioned collections, human-review commit gates, provenance receipts, 7 agent persona MCP servers exposing 100+ tools, and pluggable LLM providers (OpenAI, Anthropic, Azure OpenAI, Google AI, Cohere, Mistral, or local Ollama). DKG receipt schemas and policy routing are built directly into the platform.
- **FLARE** — confidential retrieval: AES-256-GCM encrypted vector search with Shamir K-of-M threshold oracle, Ed25519 signed grant ledger, light-cone graph authorization. 101 tests, 95.6% recall vs plaintext FAISS.
- **DKG v10** — open verifiable memory: Working Memory → Shared Memory → Verifiable Memory.

> **DKG v10.0.1 note.** As of `v10.0.1` (and first introduced in `v10.0.0-rc.17`) the daemon retired the `/api/assertion/*` routes in favour of one unified `/api/knowledge-assets` surface (OT-RFC-43), and ships redeployed contracts + a new local graph storage layout (a one-time store wipe is required on upgrade — wallet, identity, and on-chain assets are safe). This package defaults to the new surface and falls back **once** to the legacy assertion routes if a pre-v10.0.1 daemon returns `404`, so the same code works against v10.0.0 / rc.17 / rc.16 alike. See [`docs/UPGRADE_TO_RC17`](https://github.com/OriginTrail/dkg/blob/main/docs/UPGRADE_TO_RC17.md).

## What this package does

- **Default transport — local DKG v10 daemon HTTP API.** Direct HTTP to `http://127.0.0.1:9201` (v10.0.1 unified surface: `POST /api/knowledge-assets`, `POST /api/knowledge-assets/{name}/wm/write`, `POST /api/knowledge-assets/{name}/swm/share`, `POST /api/knowledge-assets/{name}/vm/publish`, `POST /api/query`). Bearer token auto-read from `~/.dkg/auth.token`. WM writes do not require an on-chain publish. Transparent one-time `404` fallback to the legacy `/api/assertion/*` routes for pre-v10.0.1 daemons.
- **Alternative transport — MCP Streamable HTTP.** Speaks JSON-RPC over SSE to a DKG node's `POST /mcp` endpoint (e.g. one fronted by `dkg mcp setup`). Selected per-call via `--transport mcp` or `DKG_TRANSPORT=mcp`.
- **MCP stdio server** (`agience-dkg-mcp`) — exposes `agience_wm_write`, `agience_promote`, `agience_search` tools for Claude Desktop, Cursor, Claude Code, OpenClaw, Hermes, and any MCP-capable agent or host. Talks to either transport.
- Writes committed Agience artifacts to DKG v10 **Working Memory** as typed `agience:` RDF Knowledge Assets — SPARQL-queryable by type, author, collection, and memory layer. Daemon transport sends N-Triples-style quads; MCP transport sends the equivalent JSON-LD shape; both encode the same predicate set.
- Promotes eligible assets to **Shared Memory** (SHARE) — daemon: `POST /api/knowledge-assets/{name}/swm/share` (the v10.0.1 / rc.17 rename of `promote`); MCP: `dkg-create` with `privacy=public`. Curator-authority, never automatic.
- Publishes finalized assets to **Verifiable Memory** (on-chain) — daemon-only: `POST /api/knowledge-assets/{name}/vm/publish`, surfaced as the `agience-dkg vm-publish` CLI command. Best-effort: a failed on-chain publish still prints its receipt for diagnosis and writes back the live UAL/stage to Agience.
- Searches across memory layers — daemon: SPARQL `SELECT` over `POST /api/query` with `GRAPH ?g` traversal of named sub-graphs; MCP: `dkg-sparql-query` with the same predicate set.
- Groups all artifacts under a stable `sessionUri` for oracle-queryable Context Graph scoping.
- Distinguishes transport success from blockchain anchoring state (`status: anchored` vs `status: pending`).
- FLARE optional path: when `policy_class = "internal-confidential"`, only derived projections reach DKG; raw content stays AES-256-GCM encrypted.

## What makes this different

| | Typical DKG integration | This submission |
|---|---|---|
| **What gets written** | Raw content or unstructured payloads | Governed, committed, typed artifacts that pass a five-dimension policy evaluation before reaching DKG |
| **Who decides what reaches DKG** | The calling code | A `PolicyMappingRecord` with policy class, promotion profile, export profile, retrieval profile, and identity profile — evaluated at commit time |
| **Sensitive content** | Omitted or manually redacted | Physically encrypted by FLARE (AES-256-GCM per-cell, Shamir threshold oracle key issuance); only derived projections reach DKG |
| **Knowledge Asset structure** | Generic `schema:Article` or flat JSON | Typed `agience:` RDF vocabulary with 8+ SPARQL-queryable predicates across Context Graphs |
| **Provenance** | None or ad-hoc | Seven receipt types (commit, grant, revoke, access, projection, publication, provenance) generated on every commit |
| **Test coverage** | Package-level tests | 87 tests in this integration package (82 unit + 5 integration). For context: Agience Core adds 11 DKG-service tests; FLARE carries 101 search tests. |

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

Add to your MCP client config (e.g. `claude_desktop_config.json`). The defaults below assume the local DKG v10 daemon — no token needs to be set in this config because the daemon transport auto-reads `~/.dkg/auth.token`:

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

To target an MCP-fronted DKG node instead, add `"DKG_TRANSPORT": "mcp"`, set `"DKG_BASE_URL": "http://localhost:8083"`, and add `"DKG_TOKEN": "<mcp-bearer>"`.

This exposes three tools: `agience_wm_write`, `agience_promote`, `agience_search`.

## CLI Quick start

```bash
# 1) Install the official DKG v10 daemon (one-time)
npm install -g @origintrail-official/dkg   # installs v10.0.1+
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

# (Optional, on-chain) publish a finalized asset to Verifiable Memory — daemon only
agience-dkg vm-publish <turnUri-from-above> --context-graph-id agience-demo
```

> **First run on rc.17 (one-time).** rc.17 is a breaking change: it redeploys contracts and uses a new local graph storage layout, so do the one-time store wipe per [`UPGRADE_TO_RC17`](https://github.com/OriginTrail/dkg/blob/main/docs/UPGRADE_TO_RC17.md) (wallet/identity/on-chain assets are safe). The daemon also downloads an Oxigraph binary into `~/.dkg/oxigraph/` on first start; if your network blocks that download the daemon appears to hang on boot — pre-seed the binary manually (place the matching `oxigraph-vX.Y.Z` executable in `~/.dkg/oxigraph/` and verify its SHA-256) to unblock startup. A `401 Unauthorized` from `GET /health` once it is up is the healthy "listening" signal.

> **Verifiable Memory (VM) caveats.** `vm-publish` is **daemon-only** (no MCP equivalent), requires the asset to be finalized and shared to SWM first, and the Context Graph must be on-chain registered with gas + TRAC and a reliable RPC. Known daemon bug: publishing to a **public** Context Graph (access-policy 0) fails with `NO_DATA_IN_SWM` — use a **private** Context Graph (access-policy 1) for VM smoke tests.

The default transport is **daemon** — direct HTTP to your local DKG v10 daemon at `http://127.0.0.1:9201`. The bearer token is auto-read from `~/.dkg/auth.token`, so you don't have to set one. WM writes do **not** require an on-chain publish, so the demo runs fully local — no TRAC staking, no testnet RPC.

> **Resolved invocation block.** Every `wm-write` call prints a `# agience-dkg wm-write — resolved invocation (copy to replay):` block to stdout *before* the HTTP call fires. It shows the fully-resolved flags (transport, base-url, agience-base-url, etc.) with bearer tokens truncated to 8 chars. Testers and reviewers can copy it directly from the terminal or any captured log to replay the exact command.

### Governed mode (drafts can't reach DKG)

Add `--from-agience-artifact <id>` to fetch a committed artifact from an Agience instance and refuse to project it unless its state is `committed`. Title, type, content, tags, and the `commit_receipt_id` are populated automatically:

> **Reviewers — hosted Agience, no local stack needed.** Sign in at **[my.agience.ai](https://my.agience.ai)** ([docs](https://docs.agience.ai)), create and *commit* an artifact, copy your bearer token, then set `AGIENCE_BASE_URL=https://my.agience.ai` and `AGIENCE_TOKEN=<token>`. The only service you run locally is the DKG v10 daemon. (Self-hosting Agience Core via Docker is still fully supported — just point `AGIENCE_BASE_URL` at your local instance instead.)

```bash
agience-dkg wm-write \
  --from-agience-artifact 9667ca6d-cc37-410f-944d-84b838fb46d0 \
  --title "ADR: DKG v10 as Verifiable Memory Substrate" \
  --artifact-type decision \
  --context-graph-id agience-demo
```

### Alternative transport — MCP Streamable HTTP

Speaks to a DKG node's `/mcp` endpoint (e.g. `dkg-node/apps/agent` or a node fronted by `dkg mcp setup`). Set `DKG_TRANSPORT=mcp`, `DKG_BASE_URL=http://localhost:8083`, and `DKG_TOKEN=<mcp-bearer>` in your `.env`, or pass `--transport mcp --base-url ... --token ...` per command.

> **WSL2 + Windows Agience tip:** if the integration runs in WSL but the Agience backend runs on Windows, `localhost` will not reach it. Use the Windows host IP: `AGIENCE_BASE_URL=http://$(ip route show | awk '/default/ {print $3}'):8081`. Check the resolved invocation block that prints before the HTTP call — if `--agience-base-url` still shows `http://localhost:8081`, re-export `AGIENCE_BASE_URL` and re-run.

## Python API

```python
from agience_dkg_integration import DkgDaemonClient, MemoryTurnRequest
from agience_dkg_integration.formatter import artifact_to_markdown, session_uri_for_collection

# Default: local DKG v10 daemon. Bearer token auto-resolves from ~/.dkg/auth.token.
client = DkgDaemonClient(base_url="http://127.0.0.1:9201")

# Alternative: MCP-fronted DKG node
# from agience_dkg_integration import DkgHttpClient
# client = DkgHttpClient(base_url="http://localhost:8083", bearer_token="<mcp-bearer>")

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
      client.py         DkgHttpClient — MCP Streamable HTTP transport (alternative)
      daemon_client.py  DkgDaemonClient — direct HTTP to local DKG v10 daemon
      models.py         Pydantic request/response models with artifact metadata
      formatter.py      artifact_to_markdown, session_uri_for_collection
      cli.py            agience-dkg CLI (wm-write, promote, vm-publish, search; --transport switch)
  tests/
    unit/               82 unit tests (governance gate, both transports, v10.0.1 KA surface + 404 fallback, vm_publish, MCP server, JSON-LD, models)
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
- [Agience Core](https://github.com/Agience/agience-core) — `src/mantle/api/dkg_integration.py` (receipt schemas), `src/mantle/services/dkg_integration_service.py` (policy mapping, projection validation + DKG projection read model), `src/facet/src/components/workspace/DkgProjectionPanel.tsx` (DKG projection panel), 11 DKG-service tests
- [FLARE Index](https://github.com/Agience/flare-index) — 101-test encrypted vector search, [research paper](https://github.com/Agience/flare-index/blob/main/paper/flare.md)

> **Fork note.** All `agience-core` and `flare-index` changes for this integration live on the author's forks ([github.com/Muffinman75](https://github.com/Muffinman75)), not the upstream `Agience/*` repos. Use the forks to review or reproduce the DKG projection read model, the `DkgProjectionPanel` UI, and the projection/publication endpoints referenced here.

## Test coverage

| Suite | Count | Requires DKG node |
|---|---|---|
| Integration package unit tests | 82 | No |
| Integration package integration tests | 5 | Yes |
| Agience Core DKG service tests | 11 | No |
| FLARE test suite | 101 | No (Docker only) |

```bash
# Unit tests (no DKG node required)
pytest package/tests/unit -v

# Integration tests (currently target the MCP transport — require an MCP-fronted DKG node)
DKG_BASE_URL=http://localhost:8083 DKG_TOKEN=<mcp-bearer> DKG_CONTEXT_GRAPH=<id> \
pytest package/tests/integration -v
```

## Design brief

See [DESIGN_BRIEF.md](DESIGN_BRIEF.md) for the full submission brief covering the three-layer architecture (Agience Core + FLARE + DKG), platform-level DKG models, receipt schema, policy mapping, promotion path, oracle-readiness, and security notes.

## Maintainer

Manoj Modhwadia ([@Muffinman75](https://github.com/Muffinman75)) — manojmodhwadia@outlook.com  
6-month support commitment from registry acceptance.
