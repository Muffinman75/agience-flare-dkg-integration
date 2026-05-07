# Design Brief — Agience FLARE × DKG v10 Integration

**Package:** `agience-flare-dkg-integration`  
**Bounty tag:** `cfi-dkgv10-r1`  
**Maintainer:** Manoj Modhwadia ([@Muffinman75](https://github.com/Muffinman75)) — manojmodhwadia@outlook.com  
**Tier target:** Flagship (8,000–10,000 TRAC)

---

## 1. Problem

Long-horizon research and knowledge-producing agents generate durable artifacts — decisions, claims, research notes, citations, summaries — but most current stacks trap them in local tools, transient chats, or private retrieval systems with no provenance, no trust gradient, and no path to collaborative verification.

DKG v10 introduces the three-tier memory model (Working Memory → Shared Memory → Verified Memory) that can serve as that shared substrate. But to be genuinely useful, it needs two things upstream:

1. A **governed authoring layer** that produces clean, typed, attributed Knowledge Assets — not raw LLM outputs.
2. A **confidential retrieval layer** that mediates what content reaches the shared substrate when the source material is sensitive.

This submission bridges three systems at the architectural level to provide both:

- **[Agience Core](https://github.com/Agience/agience-core)** — an MCP-native AI knowledge platform (858 items, 11-tool MCP server, 8 agent persona servers, ArangoDB + OpenSearch) with governed artifact authoring, versioned collections, human-review commit boundaries, and provenance receipts. DKG projection models, receipt schemas, and policy routing have been added directly to the Agience Core platform as part of this integration.

- **[FLARE](https://github.com/Agience/flare-index)** ([paper](https://github.com/Agience/flare-index/blob/main/paper/flare.md)) — cryptographically enforced AES-256-GCM encrypted vector search with Shamir K-of-M threshold oracle key issuance, Ed25519 signed hash-chained grant ledger, and light-cone graph authorization. 101-test pytest suite; 95.6% recall preservation vs plaintext FAISS on BEIR SciFact. FLARE mediates the retrieval path — when content is classified as confidential, only derived projections reach DKG.

- **DKG v10** — Working Memory, Shared Memory, and Verified Memory as the open, verifiable, collaborative memory substrate.

---

## 2. Why This Is a Flagship-Level Submission

Most DKG integrations write content to Working Memory and call it done. This submission is structurally different:

| Capability | What this means |
|---|---|
| **Governed authoring, not raw writes** | Content passes through human-review commit gates, typed artifact models, and versioned collections before it ever reaches DKG. Every commit generates a DKG-compatible receipt (actor, authority, artifact refs). |
| **Policy-controlled projection** | A five-dimension `PolicyMappingRecord` (policy class, promotion profile, export profile, retrieval profile, identity profile) governs *what* content reaches DKG, *at which stage*, and *through which retrieval path*. This is evaluated before every write — not bolted on after. |
| **Cryptographic confidentiality boundary** | When source material is sensitive, FLARE physically encrypts content at the vector-cell level (AES-256-GCM, Shamir K-of-M threshold oracle key issuance). Only derived projections reach DKG; raw content stays encrypted. This is not redaction or access control — it's cryptographic enforcement. |
| **Typed RDF Knowledge Assets** | Custom `agience:` namespace with 8+ domain-specific predicates (`agience:author`, `agience:tags`, `agience:collection`, `agience:memoryLayer`, `agience:artifactId`, etc.). Assets are SPARQL-queryable by type across Context Graphs — not opaque blobs. |
| **MCP at every layer** | Agience Core exposes 11 MCP tools + 8 persona servers; the integration exposes 3 MCP tools; the DKG node receives calls via MCP Streamable HTTP. End-to-end MCP from authoring to blockchain. |
| **155 tests across 4 suites** | 43 integration package unit tests + 5 live-node integration tests + 6 Agience Core DKG service tests + 101 FLARE tests. Policy precedence, receipt chain validation, FLARE routing, crypto, and end-to-end DKG operations are all tested. |

---

## 3. What Makes This a Platform-Level Integration

This is not a CLI wrapper around a DKG API endpoint. DKG awareness is embedded at multiple layers of the Agience platform itself.

### DKG models in Agience Core

The Agience Core platform has been extended with native DKG receipt and policy models:

**Receipt schema** (`backend/api/dkg_integration.py`, 233 lines) — seven structured receipt types track every stage of the artifact-to-DKG lifecycle:

| Receipt type | Purpose |
|---|---|
| `CommitReceipt` | Records workspace → collection commit with actor, authority, artifact refs |
| `GrantReceipt` | Records FLARE access grant issuance with subject DID, scope, capabilities |
| `RevokeReceipt` | Records FLARE grant revocation with effective timestamp |
| `AccessReceipt` | Records retrieval-path decisions (allow/deny, query mode, policy class) |
| `ProjectionReceipt` | Records artifact projection to DKG (mode, target stage, context graph, content digest) |
| `PublicationReceipt` | Records DKG publication state (written/promoted/published/finalized/failed), UAL, assertion ID |
| `ProvenanceReceipt` | Records full lineage state with receipt chain and latest DKG stage |

Every receipt carries: `actor` (principal ID, type, client ID), `authority` (authorization mode, approval ref, scope refs), `artifact_refs` (with role: source/target/receipt-parent/receipt-child), and a typed payload.

**Policy mapping** (`backend/services/dkg_integration_service.py`) — `PolicyMappingRecord` governs what content reaches DKG and how:

- `policy_class`: internal-standard, internal-confidential, export-approved, public-verifiable
- `promotion_profile`: none, wm-only, swm-eligible, vm-eligible
- `export_profile`: no-export, approval-required, derived-only, full-projection-allowed
- `retrieval_profile`: native-search, protected-search, mixed-search
- `identity_profile`: human-review-only, delegated-service, policy-automation

Policy resolution follows a precedence chain: artifact → artifact_type → collection → workspace → system default.

**Projection validation** — `validate_projection_request()` enforces that artifacts must be committed before projection, respects export policy, and requires an approval receipt.

**Commit receipts on every commit** — `workspace_service.py` calls `build_commit_receipt()` on every workspace commit, generating a DKG-compatible receipt with actor, authority, and artifact references. Every Agience commit produces the provenance chain needed for DKG publication.

**FLARE retrieval routing** — `resolve_retrieval_route()` maps policy classes to retrieval routes: `native-search` → Agience only, `protected-search` → FLARE only, `mixed-search` → Agience + FLARE. This determines whether raw content or derived projections reach DKG.

**6 unit tests** (`backend/tests/test_dkg_integration_service.py`) covering receipt chain validation, policy precedence, FLARE routing, and projection validation.

### Cryptographic retrieval layer (FLARE)

FLARE provides **cryptographically enforced access control** on the retrieval path — not an ACL layer, but physical enforcement via encryption:

- Each cluster cell of the IVF vector index is encrypted under a per-cell HKDF-derived AES-256-GCM key with `(context_id || cluster_id)` AAD binding
- Authorization is computed as reachability in a typed light-cone graph with propagation masks and path-predicate constraints
- Cell keys are issued on demand by a Shamir K-of-M threshold oracle quorum, delivered inside time-limited ECIES envelopes signed with Ed25519
- Revocation is a single signed ledger entry — no re-encryption, no key rotation, no coordination
- Constant-width oracle batches prevent query-specificity leakage
- Owner-signed storage writes with per-DID nonce replay protection
- 101-test pytest suite + benchmarks on real data (BEIR SciFact)

**Relevance to DKG:** When an Agience collection's policy is `internal-confidential`, FLARE mediates what reaches DKG. Only derived summaries or claim projections are written to Working Memory; the raw artifact content stays FLARE-encrypted. This creates a trust gradient: sensitive internal knowledge can participate in the shared memory substrate via projections, without exposing the source material.

### MCP-native at every layer

| Layer | MCP capability |
|---|---|
| **Agience Core** | 11-tool MCP server at `/mcp` (Streamable HTTP) + 8 persona servers (Astra, Sage, Verso, Aria, Nexus, Atlas, Seraph, Ophan), each a standalone FastMCP process |
| **Integration package** | MCP stdio server (`agience-dkg-mcp`) exposing `agience_wm_write`, `agience_promote`, `agience_search` — compatible with Claude Desktop, Cursor, Claude Code |
| **DKG node** | MCP Streamable HTTP at `POST /mcp` — the integration's `DkgHttpClient` speaks JSON-RPC over SSE to the DKG node's MCP endpoint |

An agent in Claude Desktop can call Agience tools to curate knowledge, call DKG tools to write/search memory, and the policy layer decides what content flows where — all via MCP.

---

## 4. Target Users

- **Research and knowledge teams** running agent-assisted workflows: literature review, architecture decisions, post-mortems, claim synthesis
- **Multi-agent systems** where one agent writes a research note or decision artifact and a downstream agent needs to retrieve and reason over it — the DKG Working Memory becomes the shared scratchpad
- **LLM-Wiki builders** implementing Karpathy's vision of a knowledge substrate natively legible to language models, continuously curated by a mixture of humans and agents
- **Autoresearch loops** where notes, claims, decisions, and citations mature iteratively — Working Memory as the draft surface, Shared Memory as the team-visible layer

**Credible first user:** The Agience platform itself — every artifact committed in an Agience workspace is a candidate for promotion into DKG Working Memory, giving any Agience user immediate access to a collaborative open memory layer.

---

## 5. Memory Layers Touched

| Layer | Role in this integration |
|---|---|
| **Working Memory** | Primary write surface. Every committed Agience artifact that meets policy is written to Working Memory via the MCP `dkg-create` tool (privacy=private) over the Streamable HTTP transport at `POST /mcp`. |
| **Shared Memory** | Promotion surface. Policy-eligible Working Memory artifacts are promoted via `dkg-create` (privacy=public) — the SHARE operation. Explicit and operator-initiated — never automatic. |
| **Verified Memory** | Forward path (Round 2). The promotion profiles, receipt lineage, and UAL references are shaped for VM promotion without a rewrite. See §9. |

---

## 6. v10 Primitives Used

| Primitive | How used |
|---|---|
| **Context Graph** | One per Agience collection. `sessionUri` links all Knowledge Assets for a collection into a coherent session, enabling oracle queries like "all decisions for collection X". |
| **Knowledge Asset** | One per Agience artifact. Written via `dkg-create` as typed JSON-LD with the `agience:` RDF vocabulary. |
| **Working Memory** | First DKG landing zone for approved artifacts. Created via `dkg-create` with `privacy=private`. |
| **Shared Memory** | Reached via SHARE — `dkg-create` with `privacy=public`. Explicit, Curator-authorized. |
| **SHARE** | Promotion from Working Memory to Shared Memory. Called explicitly; never triggered silently. |
| **PUBLISH** | Not called in Round 1. Described in the promotion path for Round 2 readiness. |
| **Curator** | Authority model respected: no SHARE or PUBLISH without explicit caller intent. |
| **UAL** | Preserved as the stable artifact reference. Receipt lineage traces back to the originating Agience artifact via the `ProvenanceReceipt` chain. |

---

## 7. Fit with LLM-Wiki / Autoresearch Direction

Karpathy's LLM-Wiki frames a knowledge substrate natively legible to language models, continuously curated by humans and agents. The v10 memory model maps this directly:

- **Working Memory** = agent-populated draft surface
- **Shared Memory** = team-gossiped collaborative layer
- **Verified Memory** = chain-anchored trustable layer

Agience provides the governed loop producing clean, attributed artifacts with stable IDs, typed structure, and provenance metadata — making DKG Working Memory useful rather than a dump of raw LLM outputs. FLARE provides the confidentiality boundary so that sensitive content can still participate via projections. Downstream agents retrieve, reason over, and act on this knowledge via Context Graph SPARQL queries.

---

## 8. Architecture

### Three-layer data flow

```
Agience Core (governed authoring)
  │
  │  artifact committed → commit receipt generated
  │  policy evaluated → projection validated
  │
  ├── FLARE (confidential retrieval, optional)
  │     │  policy_class = "internal-confidential"
  │     │  → raw content stays encrypted
  │     │  → derived summary/claim projected
  │     │
  ▼     ▼
Integration Package (bridge)
  │
  │  formatter.py → typed JSON-LD (agience: vocabulary)
  │  client.py → MCP Streamable HTTP to DKG node
  │
  ▼
DKG v10 Node (POST /mcp)
  │  dkg-create (privacy=private) → Working Memory
  │  dkg-create (privacy=public)  → Shared Memory (SHARE)
  │  dkg-sparql-query             → Search across layers
  ▼
Blockchain (testnet anchoring)
```

### Integration package components

- **`mcp_server.py`** — MCP stdio server exposing `agience_wm_write`, `agience_promote`, `agience_search` as MCP tools. Compatible with Claude Desktop, Cursor, Claude Code, and any MCP host.
- **`client.py`** — `DkgHttpClient` calling `dkg-create` and `dkg-sparql-query` over MCP Streamable HTTP with SSE stream parsing.
- **`formatter.py`** — structured Markdown with RDF-extractable headers.
- **`cli.py`** — `wm-write`, `promote`, `search` commands via `typer`.
- **`models.py`** — Pydantic request/response models with artifact metadata fields.

### Typed JSON-LD Knowledge Assets

Knowledge Assets use a typed `agience:` RDF namespace (`https://agience.ai/ontology/`):

```json
{
  "@context": {
    "schema": "https://schema.org/",
    "agience": "https://agience.ai/ontology/"
  },
  "@type": "agience:architecture-decision",
  "@id": "agience:my-collection/art-001",
  "agience:contextGraphId": "my-collection",
  "agience:memoryLayer": "wm",
  "agience:artifactId": "art-001",
  "agience:author": "Manoj Modhwadia",
  "agience:tags": ["architecture", "dkg-v10"],
  "agience:collection": "agience-architecture",
  "schema:name": "Architecture Decision: DKG v10 as shared memory substrate",
  "schema:text": "We will use DKG v10 Working Memory as the shared knowledge substrate..."
}
```

This makes assets SPARQL-queryable by type across Context Graphs — e.g. "find all `agience:architecture-decision` assets where `agience:author` = 'Manoj Modhwadia'".

### Error handling

The integration distinguishes MCP transport success from blockchain anchoring state:

- **`status: "anchored"`** — DKG node accepted and anchored the Knowledge Asset; UAL returned.
- **`status: "pending"`** — MCP transport succeeded but blockchain anchoring failed (e.g. testnet RPC down). The `error` field explains the failure. The Knowledge Asset may anchor once the RPC recovers.

### Transport

MCP Streamable HTTP — `POST /mcp` with `Accept: application/json, text/event-stream`. Tool call responses are delivered as SSE streams; the client reads the first `data:` event containing the JSON-RPC result.

---

## 9. Promotion Path and Oracle-Readiness

### Working Memory → Shared Memory (SHARE)

An Agience artifact reaches Shared Memory when:
1. It has been committed in Agience (explicit human-review boundary)
2. Its collection policy marks it `swm-eligible` via `PolicyMappingRecord.promotion_profile`
3. The operator explicitly calls `agience-dkg promote <turnUri> --context-graph-id <id>`

This calls `dkg-create` with `privacy=public` — a Curator-authorized operation. Nothing is promoted automatically.

### Shared Memory → Verified Memory (PUBLISH, Round 2)

The integration is pre-shaped for Verified Memory:

- The `turnUri` (UAL) chain is preserved through all promotions
- The receipt schema records `ProjectionReceipt` and `PublicationReceipt` types linking `assertion_id`, `ual`, `dkg_stage`, and `publish_state`
- Policy profiles (`vm-eligible`) and export profiles (`full-projection-allowed`) are already defined in `PolicyMappingRecord`

### Oracle-readiness

Every Knowledge Asset written by this package:
- Has a stable UAL preserved in the `ProvenanceReceipt` chain
- Is scoped to a Context Graph via `contextGraphId`
- Uses `sessionUri` to link all assets for an Agience collection
- Uses typed `agience:` RDF predicates that produce predictable, queryable triples

---

## 10. Terminology

All code and documentation uses exact DKG v10 vocabulary:

- **Context Graph** — one per Agience collection
- **Knowledge Asset** — one per Agience artifact
- **Working Memory / Shared Memory / Verified Memory** — never "private/public/chain"
- **SHARE** — promotion from Working Memory to Shared Memory
- **PUBLISH** — promotion toward Verified Memory (Round 2)
- **Curator** — the authority required for SHARE/PUBLISH

The CLI `--layer` flag accepts `wm` / `swm` as usability shorthands. All API responses, documentation, and internal code use the full v10 terms. The Agience-side terms (`collection`, `artifact`, `commit`) are explicitly not treated as DKG synonyms — they are upstream governance concepts.

---

## 11. Security Notes

- All credentials (`DKG_TOKEN`, `DKG_BASE_URL`) are read from environment variables — never hardcoded, never logged
- No SHARE or PUBLISH operation is performed automatically — all promotion is explicit and operator-initiated
- No `postinstall` or `preinstall` scripts in the package
- **Declared network egress:** DKG node endpoint only. Optional FLARE service endpoint only when `retrieval_profile = protected-search` is explicitly configured. No other external domains.
- **Declared write authority:**
  - `POST /mcp` → `dkg-create` (privacy=private) — write Working Memory
  - `POST /mcp` → `dkg-create` (privacy=public) — SHARE to Shared Memory (Curator-authorized)
  - `POST /mcp` → `dkg-sparql-query` — search (read only)
  - `GET /health` — ping/health check only
- **MCP server (stdio):** reads `DKG_TOKEN` and `DKG_BASE_URL` from environment only; credentials are never accepted as tool arguments
- No dynamic code loading, no `eval` on external input, no internal DKG package imports
- FLARE confidential path: when enabled, raw artifact content stays FLARE-encrypted; only derived projections reach DKG
- `pip audit --production` clean on package dependencies
- CI pipeline: GitHub Actions runs unit tests across Python 3.11–3.13, dependency audit, and build verification

---

## 12. Test Coverage

| Suite | Count | Scope |
|---|---|---|
| Integration package unit tests | 43 | MCP server tool definitions and message routing, JSON-LD vocabulary generation, error status detection, client operations, Pydantic models, formatter |
| Integration package integration tests | 5 | End-to-end against live DKG node: WM write, SWM promote, search, health check |
| Agience Core DKG service tests | 6 | Receipt chain validation, policy precedence, FLARE retrieval routing, projection validation |
| FLARE test suite | 101 | Crypto, identity, wire protocol, light cone, oracle service + threshold + peer protocol, signed ledger, storage signing, multi-endpoint failover, sealed key storage, padding, cell-key TTL, caching, centroid gate, end-to-end, concurrent revocation |

---

## 13. Maintenance Commitment

**Maintainer:** Manoj Modhwadia ([@Muffinman75](https://github.com/Muffinman75)) — manojmodhwadia@outlook.com  
**Support window:** 6 months from registry acceptance  
**Issue response:** within 5 business days for reported defects  
**Versioning:** semantic versioning; breaking changes are major version bumps with migration notes  
**Scope:** compatibility with supported DKG v10 public interfaces — `POST /mcp` (MCP Streamable HTTP transport), tools `dkg-create` and `dkg-sparql-query`, and `GET /health`

---

## 14. Round 2 Roadmap

**Verified Memory (PUBLISH):** Extend `client.py` with `shared_memory_publish()`. The receipt schema, UAL chain preservation, and `vm-eligible` policy profile are already in place.

**End-to-end FLARE → DKG pipeline:** Wire the FLARE projection validation into a live pipeline that automatically projects derived summaries to DKG Working Memory when confidential artifacts are committed.

**Agience Core commit hook:** Fire DKG Working Memory writes automatically on workspace commit for collections with `promotion_profile >= wm-only`, creating a zero-friction path from Agience to DKG.

**Timeline:** Post-Round-1 acceptance. These extensions leverage the existing policy model and client — no architectural rewrite required.
