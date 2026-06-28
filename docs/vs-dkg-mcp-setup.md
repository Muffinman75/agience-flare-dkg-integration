# `dkg mcp setup` vs Agience FLARE × DKG v10 Integration

**Last updated:** 28 Jun 2026 (verified against DKG v10.0.1, which retired the `/api/assertion/*` routes for the unified `/api/knowledge-assets` surface and completed the Working → Shared → Verifiable Memory model)

> **Fork note.** The `agience-core` / `flare-index` components referenced here (governance gate, `CommitReviewDialog`, DKG projection panel, receipt schema) live on the author's forks at [github.com/Muffinman75](https://github.com/Muffinman75), not the upstream `Agience/*` repos.

On 7 May 2026 OriginTrail shipped `dkg mcp setup` — a two-command path that wires any MCP-compatible client (Cursor, Claude Desktop, Claude Code, Cline, Codex, Windsurf, VS Code Copilot Chat) to DKG Working Memory:

```bash
npm install -g @origintrail-official/dkg
dkg mcp setup
```

This is excellent and solves the transport problem. **This integration is the governance layer above it** — what determines what reaches DKG, why, and under what authority and confidentiality constraints.

---

## Head-to-head

| Capability | `dkg mcp setup` | Agience FLARE × DKG v10 |
|---|---|---|
| **MCP transport to DKG** | ✅ Two-command install | ✅ MCP stdio server (compatible, complementary) |
| **Works with Claude / Cursor / Cline / Codex / Windsurf / Copilot Chat** | ✅ | ✅ |
| **Works with OpenClaw / Hermes / any MCP agent** | ✅ Direct write | ✅ Via Agience's persona MCP servers — any MCP-capable agent deposits into Agience, then this integration's `agience_wm_write` projects only human-committed artifacts to DKG |
| **Human-review commit boundary** | ❌ Any agent calls `dkg-create` directly | ✅ Workspace → Collection commit gate; nothing reaches DKG without explicit human approval |
| **Structured commit review** | ❌ No review surface | ✅ `CommitReviewDialog` shows every changed artifact, its target collection, and provenance attribution before the human confirms |
| **Policy-controlled projection** | ❌ None | ✅ Five-dimension `PolicyMappingRecord` evaluated before every write |
| **Cryptographic confidentiality boundary** | ❌ Plaintext content reaches DKG | ✅ FLARE AES-256-GCM cell-level encryption + Shamir K-of-M threshold oracle (101 tests) |
| **Typed RDF Knowledge Assets** | ❌ Generic JSON-LD | ✅ `agience:` namespace, 8+ SPARQL-queryable predicates |
| **Provenance / receipt chain** | ❌ None | ✅ Seven receipt types link every commit to its UAL |
| **Visibility — "what's in my Working Memory and why?"** | ❌ Opaque | ✅ Every artifact visible in Agience UI before projection; receipt schema is auditable |

---

## What governance buys you

### 1. Commit-gated authoring

Without governance, an MCP-connected agent can `dkg-create` anything at any time. With Agience Core upstream, every artifact passes:

1. Drafted in a workspace (Agience artifacts have a `state` field with `{draft, committed, archived}`, enforced server-side in `entities/artifact.py`)
2. Authored via the Palette — Prompts, Instructions, Context, and Input/Output panels invoke the configured LLM (any provider Agience supports — OpenAI, Anthropic, Azure OpenAI, Google AI, Cohere, Mistral, or local Ollama) and write the result back as draft artifacts the human can edit
3. Reviewed in `CommitReviewDialog`, which surfaces every changed artifact, its target collection, provenance attribution, and any commit warnings
4. **Explicit human commit** to a versioned collection — the `committed` state transition is the governance boundary
5. On projection, this integration tags the JSON-LD `@type` (e.g. `agience:architecture-decision`) from the operator-supplied `--artifact-type` flag and evaluates `PolicyMappingRecord`
6. Only then projected to DKG, with a `ProjectionReceipt` in the chain

This directly answers the bounty's design principle of "human-in-the-loop is structural" rather than prompt-based.

### 2. Policy-controlled projection

`PolicyMappingRecord` answers five questions for every artifact, with precedence chain (artifact → artifact_type → collection → workspace → system default):

| Dimension | Values | Purpose |
|---|---|---|
| `policy_class` | internal-standard, internal-confidential, export-approved, public-verifiable | Sensitivity tier |
| `promotion_profile` | none, wm-only, swm-eligible, vm-eligible | How far in the trust gradient this can travel |
| `export_profile` | no-export, approval-required, derived-only, full-projection-allowed | What form reaches DKG |
| `retrieval_profile` | native-search, protected-search, mixed-search | Whether FLARE mediates retrieval |
| `identity_profile` | human-review-only, delegated-service, policy-automation | Who is allowed to commit |

Reviewers can audit every projection by reading the receipts.

### 3. Cryptographic confidentiality

For sensitive material, FLARE physically encrypts content at the IVF cluster-cell level (AES-256-GCM, per-cell HKDF-derived key with `(context_id || cluster_id)` AAD binding). Authorization is reachability in a typed light-cone graph; cell keys are issued by a Shamir K-of-M threshold oracle quorum inside time-limited Ed25519-signed ECIES envelopes. Revocation is a single signed ledger entry — no re-encryption.

When `policy_class = "internal-confidential"`, raw content stays FLARE-encrypted; only derived projections (summary, claim) reach DKG. This is cryptographic enforcement, not redaction or ACL.

### 4. Typed RDF Knowledge Assets

Where `dkg-create` accepts generic JSON-LD, this integration writes typed `agience:` Knowledge Assets. The `@type` is supplied by the operator/agent through the CLI (`--artifact-type`) or MCP tool argument (`artifact_type`) and asserted by this integration when constructing the JSON-LD payload. This knowledge-domain `@type` (e.g. `research-note`, `decision`, `claim`) is a *different axis* from Agience's own native taxonomy: Agience types every artifact by `content_type` — a media-type system (e.g. `text/markdown`, `application/vnd.agience.person+json`) that classifies *format*, not knowledge role. The integration deliberately asserts the knowledge-domain `@type` rather than reusing the platform content-type, keeping the DKG vocabulary purpose-built for research/knowledge assets:

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
  "schema:text": "..."
}
```

This makes assets SPARQL-queryable by type across Context Graphs, e.g. *"all `agience:architecture-decision` assets where `agience:author` = 'Manoj' in collection `agience-architecture`"*.

### 5. Visibility and stats

Users have asked in the OriginTrail Telegram channel: *"how do I know what's being recorded as Working Memory? how do I know it's saving me tokens?"* This integration directly addresses that:

- Every artifact is visible in the Agience UI **before** it reaches DKG
- The receipt chain (`CommitReceipt` → `ProjectionReceipt` → `PublicationReceipt`) is auditable
- Each `MemoryTurnResult` returns `status: "anchored"` or `status: "pending"` so callers can distinguish MCP transport success from blockchain anchoring state

---

## Complementarity with rc.6 on-chain author attestation

DKG v10.0.0-rc.6 (10 May 2026) added cryptographic publisher attribution to canonical Knowledge Assets: every finalized KC now carries a `dkg:authoredBy` triple derived from an EIP-712 author attestation, with the recovered author address indexed in the `KCCreated` event topic (CHANGELOG entry for rc.6, lines 14–15).

This composes cleanly with what this integration adds. The on-chain attestation answers *"which agent or wallet signed this publish?"*. This integration's `agience:commitReceiptId` predicate, threaded through `MemoryTurnRequest → DkgHttpClient.memory_turn` JSON-LD, answers *"which Agience commit, by which human, in which workspace, authorised this content to be projected at all?"*.

Together they form a two-layer provenance chain on the canonical asset:

- `dkg:authoredBy` — cryptographic publisher identity (DKG layer, EIP-712-signed)
- `agience:commitReceiptId` → resolves to a `CommitReceipt` with actor, authority, artifact references (Agience layer, ArangoDB-backed, server-enforced via `check_access`)

A reviewer can answer *"who, with what authority, decided this was fit for shared memory?"* without reading any prompt, prompt-template, or LLM trace — by reading two RDF predicates.

---

## When to use which

**Use `dkg mcp setup`** when you want any MCP-capable agent to read and write DKG Working Memory directly, with no upstream governance. Lowest friction, fastest path.

**Use this integration** when:

- You want a **commit boundary** between agent output and DKG
- You need **typed, attributed artifacts** rather than free-form payloads
- You handle **sensitive content** that should not reach DKG in plaintext
- You need an **audit trail** linking every Knowledge Asset back to a human-approved source
- You want **typed RDF queries** rather than opaque blob retrieval

The two are complementary. `dkg mcp setup` gives you the MCP transport layer to the DKG node. This integration gives you the governed, typed, auditable authoring layer above it.

---

## See also

- [Design brief](../DESIGN_BRIEF.md)
- [Security notes](security-notes.md)
- [Demo script](demo-script.md)
- [Agience Core](https://github.com/Agience/agience-core)
- [FLARE Index](https://github.com/Agience/flare-index)
- [OriginTrail DKG v10](https://github.com/OriginTrail/dkg)
