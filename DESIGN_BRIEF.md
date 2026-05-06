# Design Brief — Agience FLARE × DKG v10 Integration

**Package:** `agience-flare-dkg-integration`  
**Bounty tag:** `cfi-dkgv10-r1`  
**Maintainer:** Manoj Modhwadia ([@Muffinman75](https://github.com/Muffinman75)) — manojmodhwadia@outlook.com  
**Tier target:** Flagship (8,000–10,000 TRAC)

---

## 1. Problem

Long-horizon research and knowledge-producing agents generate durable artifacts — decisions, claims, research notes, citations, summaries — but most current stacks trap them in local tools, transient chats, or private retrieval systems with no provenance, no trust gradient, and no path to collaborative verification.

Two platforms already exist that partially solve this independently:

- **[Agience](https://github.com/Agience/agience-core)** is an MCP-native AI knowledge platform providing governed artifact authoring, collection management, human-review commit boundaries, and provenance receipts. Artifacts mature through draft → commit lifecycle with explicit actor, authority, and approval tracking.
- **[FLARE](https://github.com/Agience/flare-index)** ([paper](https://github.com/Agience/flare-index/blob/main/paper/flare.md)) provides cryptographically enforced, AES-256-GCM encrypted vector search with path-predicate light-cone authorization and a propagation-mask permission model. It sits between the agent and the knowledge store, mediating access without exposing plaintext.

What neither provides alone is a **shared, open, verifiable memory substrate** that multiple agents can read, write, and collaboratively mature over time. That is precisely what DKG v10 Working Memory and Shared Memory offer.

This integration bridges all three: Agience provides the governed authoring and provenance layer; FLARE provides optional confidential retrieval mediation; DKG v10 provides the open collaborative memory substrate.

---

## 2. Target Users

- **Research and knowledge teams** running agent-assisted workflows: literature review, architecture decisions, post-mortems, claim synthesis
- **Multi-agent systems** where one agent writes a research note or decision artifact and a downstream agent needs to retrieve and reason over it — the DKG Working Memory becomes the shared scratchpad
- **LLM-Wiki builders** implementing Karpathy's vision of a knowledge substrate natively legible to language models, continuously curated by a mixture of humans and agents
- **Autoresearch loops** where notes, claims, decisions, and citations mature iteratively — Working Memory as the draft surface, Shared Memory as the team-visible layer

**Credible first user:** The Agience platform itself — every artifact committed in an Agience workspace is a candidate for promotion into DKG Working Memory via this integration, giving any Agience user immediate access to a collaborative open memory layer.

---

## 3. Memory Layers Touched

| Layer | Role in this integration |
|---|---|
| **Working Memory** | Primary write surface. Every committed Agience artifact that meets policy can be written to Working Memory via `POST /api/memory/turn`. This is the default, lowest-friction path. |
| **Shared Memory** | Promotion surface. Policy-eligible Working Memory artifacts are promoted via `POST /api/assertion/:name/promote` (the SHARE operation). This is explicit and operator-initiated — never automatic. |
| **Verified Memory** | Forward path only (Round 2). The promotion profiles, receipt lineage, and UAL references in this integration are shaped for VM promotion without a rewrite. See §7. |

---

## 4. v10 Primitives Used

| Primitive | How used |
|---|---|
| **Context Graph** | One per Agience collection. The `sessionUri` links all Knowledge Assets for a collection into a coherent session in the Context Graph, enabling oracle queries like "all decisions for collection X". |
| **Knowledge Asset** | One per Agience artifact. Written via `POST /api/memory/turn` as structured Markdown. The DKG node extracts RDF triples from consistent field headers. |
| **Working Memory** | The first DKG landing zone for approved artifacts. |
| **Shared Memory** | Reached via the SHARE operation (`/api/assertion/:name/promote`). Explicit, Curator-authorized. |
| **SHARE** | The promotion operation from Working Memory to Shared Memory. Called explicitly by the operator or CI; never triggered silently. |
| **PUBLISH** | Not called in Round 1. Described in the promotion path for Round 2 readiness. |
| **Curator** | Authority model respected: no SHARE or PUBLISH operation is invoked without explicit caller intent. |
| **UAL** | The `turnUri` returned by `/api/memory/turn` is preserved as the stable artifact reference. Receipt lineage traces back to the originating Agience artifact. |

---

## 5. Fit with LLM-Wiki / Autoresearch Direction

Karpathy's LLM-Wiki frames a knowledge substrate natively legible to language models, continuously curated by humans and agents. The v10 memory model maps this directly:

- **Working Memory** = agent-populated draft surface
- **Shared Memory** = team-gossiped collaborative layer  
- **Verified Memory** = chain-anchored trustable layer

Agience provides the governed loop producing clean, attributed artifacts with stable IDs, typed structure, and provenance metadata — making DKG Working Memory useful rather than a dump of raw LLM outputs. Downstream agents can retrieve, reason over, and act on this knowledge via Context Graph queries.

---

## 6. Architecture

**Data flow:** Agience artifact (committed) → `formatter.py` (Markdown KA) → `client.py` → DKG v10 HTTP API.

**Components:**
- `formatter.py`: Structured Markdown with RDF-extractable headers
- `client.py`: Thin wrapper around `POST /api/memory/turn`, `/api/assertion/:name/promote`, `/api/memory/search`
- `cli.py`: `wm-write`, `promote`, `search` commands

**Optional FLARE path:** When `policy_class = "internal-confidential"`, raw content stays FLARE-encrypted; only derived summaries are projected to DKG.

**Interfaces:** DKG v10 node HTTP API only. No internal DKG package imports.

---

## 7. Promotion Path and Oracle-Readiness

### Working Memory → Shared Memory (SHARE)

An Agience artifact reaches Shared Memory when:
1. It has been committed in Agience (explicit human-review boundary)
2. Its collection policy marks it `swm-eligible`
3. The operator (or CI pipeline) explicitly calls `agience-dkg promote <turnUri> --context-graph-id <id>`

This calls `POST /api/assertion/:name/promote` — a Curator-authorized operation. Nothing is promoted automatically.

### Shared Memory → Verified Memory (PUBLISH, Round 2)

Once in Shared Memory, an artifact can be shaped for Verified Memory publication via `POST /api/shared-memory/publish`. The integration is pre-shaped for this:

- The `turnUri` (UAL) chain is preserved through all promotions — the on-chain record can trace back to the original Agience artifact
- The Agience receipt schema records `projection_receipt` and `publication_receipt` types that link `assertion_id`, `ual`, and `dkg_stage`
- Policy profiles (`vm-eligible`) and export profiles (`full-projection-allowed`) are already defined — enabling the same integration code to support Round 2 without a rewrite

### Oracle-readiness

Every Knowledge Asset written by this package:
- Has a stable UAL (`turnUri` from `/api/memory/turn`)
- Is scoped to a Context Graph via `contextGraphId`, making it consumable by a context oracle querying that graph
- Uses `sessionUri` to link all assets for an Agience collection, enabling oracle queries like "all architecture decisions for collection X"
- Uses consistent Markdown field headers (`**Type:**`, `**Author:**`, `**Tags:**`, `**Collection:**`) that produce predictable RDF triples for semantic queries

---

## 8. Terminology

All code and documentation uses exact DKG v10 vocabulary:

- **Context Graph** — one per Agience collection
- **Knowledge Asset** — one per Agience artifact
- **Working Memory / Shared Memory / Verified Memory** — never "private/public/chain"
- **SHARE** — promotion from Working Memory to Shared Memory
- **PUBLISH** — promotion toward Verified Memory (Round 2)
- **Curator** — the authority required for SHARE/PUBLISH

**Terminology note:** The CLI `--layer` flag accepts `wm` / `swm` as usability shorthands. All API responses, documentation, and internal code use the full v10 terms (Working Memory, Shared Memory). This deviation is justified as follows: (a) CLI ergonomics — command-line users expect concise flags; (b) no ambiguity — the mapping is 1:1 and documented; (c) API contracts remain pure — the shorthand is resolved to the full term before any DKG API call.

The Agience-side terms (`collection`, `artifact`, `commit`) are explicitly not treated as DKG synonyms. They are upstream governance concepts that produce artifacts eligible for DKG projection.

---

## 9. Security Notes

- All credentials (`DKG_TOKEN`, `DKG_BASE_URL`) are read from environment variables — never hardcoded, never logged
- No SHARE or PUBLISH operation is performed automatically — all promotion is explicit and operator-initiated
- No `postinstall` or `preinstall` scripts in the package
- **Declared network egress:** DKG node endpoint only. Optional FLARE service endpoint only when `retrieval_profile = protected-search` is explicitly configured. No other external domains.
- **Declared write authority:**
  - `POST /api/memory/turn` — write Working Memory (default operation)
  - `POST /api/assertion/:name/promote` — SHARE to Shared Memory (Curator-authorized, explicit only)
  - `POST /api/memory/search` — read only
  - `GET /api/agents` — ping/health check only
- No dynamic code loading, no `eval` on external input, no internal DKG package imports
- FLARE confidential path: when enabled, raw artifact content stays FLARE-protected; only a derived summary or claim projection is written to DKG Working Memory
- `pip audit --production` clean on package dependencies

---

## 10. Maintenance Commitment

**Maintainer:** Manoj Modhwadia ([@Muffinman75](https://github.com/Muffinman75)) — manojmodhwadia@outlook.com  
**Support window:** 6 months from registry acceptance  
**Issue response:** within 5 business days for reported defects  
**Versioning:** semantic versioning; breaking changes are major version bumps with migration notes  
**Scope:** compatibility with supported DKG v10 public interfaces — `POST /api/memory/turn`, `POST /api/assertion/:name/promote`, `POST /api/memory/search`

---

## 11. Round 2 Roadmap

**Verified Memory (PUBLISH):** Extend `client.py` with `shared_memory_publish()` calling `POST /api/shared-memory/publish`. The receipt schema and UAL chain preservation are already in place.

**OpenClaw Integration:** Add MCP server wrapper exposing `wm-write`, `promote`, `search` as MCP tools. This enables any MCP-capable agent (Claude Desktop, Cline, etc.) to read/write DKG memory directly.

**Hermes Integration:** Implement `hermes-dkg` bridge for the Hermes agent framework, allowing Hermes agents to use DKG as their shared memory substrate.

**Timeline:** Post-Round-1 acceptance. These extensions leverage the same core `client.py` and `formatter.py` — no architectural rewrite required.
