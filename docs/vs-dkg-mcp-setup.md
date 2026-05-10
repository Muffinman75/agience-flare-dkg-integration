# `dkg mcp setup` vs Agience FLARE × DKG v10 Integration

**Last updated:** 10 May 2026

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
| **Human-review commit boundary** | ❌ Any agent calls `dkg-create` directly | ✅ Workspace → Collection commit gate; nothing reaches DKG without explicit human approval |
| **Typed artifact extraction** | ❌ Free-form payloads | ✅ Decision / claim / constraint / action unit artifacts with evidence quotes |
| **Policy-controlled projection** | ❌ None | ✅ Five-dimension `PolicyMappingRecord` evaluated before every write |
| **Cryptographic confidentiality boundary** | ❌ Plaintext content reaches DKG | ✅ FLARE AES-256-GCM cell-level encryption + Shamir K-of-M threshold oracle (101 tests) |
| **Typed RDF Knowledge Assets** | ❌ Generic JSON-LD | ✅ `agience:` namespace, 8+ SPARQL-queryable predicates |
| **Provenance / receipt chain** | ❌ None | ✅ Seven receipt types link every commit to its UAL |
| **Visibility — "what's in my Working Memory and why?"** | ❌ Opaque | ✅ Every artifact visible in Agience UI before projection; receipt schema is auditable |

---

## What governance buys you

### 1. Commit-gated authoring

Without governance, an MCP-connected agent can `dkg-create` anything at any time. With Agience Core upstream, every artifact passes:

1. Drafted in a workspace
2. Optionally extracted into typed unit artifacts (decision, claim, constraint)
3. Reviewed in commit preview (warns on missing provenance)
4. **Explicit human commit** to a versioned collection
5. Policy evaluated against `PolicyMappingRecord`
6. Only then projected to DKG with a `ProjectionReceipt`

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

Where `dkg-create` accepts generic JSON-LD, this integration writes typed `agience:` Knowledge Assets:

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
