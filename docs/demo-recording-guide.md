# Demo Recording Guide — Agience × DKG v10 Integration

**Last updated:** 2026-05-13 (post end-to-end success)

This is the practical, scene-by-scene shooting script for the bounty submission video. It reflects the actual flow that was proved end-to-end on 2026-05-12: an OpenAI-powered LLM in Agience generates an Architecture Decision Record, a human commits it through Agience's governance boundary, and the integration projects it as a typed `agience:` Knowledge Asset to DKG v10 — refusing to project anything still in `draft`.

The legacy CLI-only walkthrough is preserved at [`demo-script.md`](demo-script.md). This file supersedes it for recording purposes.

---

## 0. One-time setup (do this once, never again)

These edits make the per-session shell exports unnecessary. After this, every recording attempt is just "start three things, click record."

### 0.1 Agience backend `.env`

File: `agience-core/.env`

Already contains `OPENAI_API_KEY=...`. Verify by running:

```powershell
Get-Content C:\Users\manoj\Repos\agience\agience-core\.env
```

If `OPENAI_API_KEY` isn't there, add the line. Aria's chat handler reads this on startup; without it, the agentic chat returns `"No LLM connection available"`.

### 0.2 DKG agent `.env`

File: `dkg/dkg-node/apps/agent/.env`

The Agience backend defaults to port 8081, and so does the DKG agent — that's the collision we kept hitting. Open the file in WSL or your editor and change one line:

```
PORT=8083
```

Confirmed working values for the rest of the file are already there (`DKG_OTNODE_URL`, wallets, `DEFAULT_PUBLISH_BLOCKCHAIN`). Don't touch them.

### 0.3 Integration package `.env`

File: `integration/package/.env`

Copy from the template:

```powershell
Copy-Item C:\Users\manoj\Repos\agience\integration\package\.env.example `
          C:\Users\manoj\Repos\agience\integration\package\.env
```

Then edit and fill in `AGIENCE_TOKEN` (your `agc_...` key minted from the UI or `POST /api-keys`). The other values in the template (`DKG_BASE_URL=http://localhost:8083`, `DKG_TOKEN`, `DKG_CONTEXT_GRAPH=agience-demo`, `AGIENCE_BASE_URL=http://localhost:8081`) match the local setup we verified.

The `agience-dkg` CLI and `agience-dkg-mcp` server now auto-load this file at startup. Existing shell exports still take precedence, so you can override any value per-command if needed.

### 0.4 Reinstall the package (only after pulling new code)

```powershell
cd C:\Users\manoj\Repos\agience\integration\package
pip install -e .
```

This picks up the new `python-dotenv` dependency and the auto-loader.

---

## 1. Start the three services (per recording session)

Open three terminals. None of them need any `$env:` exports any more.

### Terminal 1 — Agience backend

```powershell
cd C:\Users\manoj\Repos\agience\agience-core
.\agience.bat dev
```

Wait until the backend logs:

```
Application startup complete.
Phase 4 search initialization complete.
```

Open the UI at `http://localhost:5173` and log in. Confirm the Inbox workspace exists.

### Terminal 2 — DKG agent (WSL)

```bash
cd /mnt/c/Users/manoj/Repos/agience/dkg/dkg-node/apps/agent
source ~/.nvm/nvm.sh && nvm use 22
node dist/index.js
```

Wait for `Server running at http://localhost:8083/`.

Sanity check from PowerShell:

```powershell
Invoke-RestMethod http://localhost:8083/health
```

### Terminal 3 — recording terminal

```powershell
cd C:\Users\manoj\Repos\agience\integration\package
```

Verify the auto-loader picks up your `.env`:

```powershell
agience-dkg wm-write --help | Select-Object -First 5
```

(no `Error: DKG bearer token required` means the .env loaded fine.)

---

## 2. Recording — scene by scene

Total target length: **8–10 minutes.** Tight, focused, no dead air.

### Scene 1 — Why this exists (60–75s, slide / talking head)

> "Enterprise AI has a memory and trust problem. LLMs generate output at scale, but that output has no identity, no provenance, and no chain of custody. Two agents on the same team can't even agree on what the team decided yesterday."
>
> "Agience solves the human-governance side: every artifact is typed, versioned, and crosses an explicit commit boundary under human review. OriginTrail's DKG v10 solves the cross-organisation side: a verifiable, decentralised knowledge graph anyone can query."
>
> "This integration bridges them. Committed Agience artifacts — and only committed ones — project to DKG as typed `agience:` RDF Knowledge Assets, with a commit receipt linking the on-chain record back to the human-approved version."

Show the architecture diagram from `integration/DESIGN_BRIEF.md` if you have one ready.

### Scene 2 — The three running services (30s)

Quick cuts through the three terminals:

- Agience backend log line: `Application startup complete.`
- DKG agent log line: `Server running at http://localhost:8083/`
- The Agience UI logged in, Inbox workspace visible

Narrate: *"Three components running locally: Agience backend on 8081, DKG agent node on 8083, and the integration CLI."*

### Scene 3 — LLM generates an artifact inside Agience (90s)

In the Agience UI, navigate to the **Inbox** workspace. Open the chat / "Ask anything" surface. Paste:

```
Write an architecture decision record for using DKG v10 as a shared
verifiable memory substrate for multi-agent AI systems. Include:
context, decision, rationale, and consequences. Under 300 words.
Format as Markdown.
```

Press send. Wait for Aria's tool calls to land. A new **draft** artifact appears in the workspace with the ADR content.

Narrate: *"The OpenAI-powered chat agent calls Agience's `create_artifact` MCP tool. The result is a real, typed artifact in the workspace — but it's a draft. Nothing has crossed the trust boundary yet."*

Click into the new artifact. Show its state in the right-hand panel: **`draft`**.

### Scene 4 — The governance gate refuses to project a draft (45s)

Cut to Terminal 3. Grab the draft artifact's ID from the URL or backend log:

```powershell
$artifactId = "<the-draft-artifact-id>"
```

Run:

```powershell
agience-dkg wm-write `
  --from-agience-artifact $artifactId `
  --title "ADR: DKG v10 as Verifiable Memory Substrate" `
  --artifact-type "decision" `
  --context-graph-id $env:DKG_CONTEXT_GRAPH
```

Expected output:

```
Governance error: Artifact '<id>' is in state 'draft', not 'committed'.
Only committed Agience artifacts may be projected to DKG.
```

Narrate: *"The integration refuses. This is the whole point: drafts cannot become shared memory. Governance is enforced at the boundary, not by policy."*

### Scene 5 — Human commit (45s)

Back in the UI. Click **Commit** on the workspace. The Commit Preview dialog opens, listing the draft and its target collection.

Narrate: *"The commit preview is the human-review gate. It surfaces what's about to become governed and where it's going."*

Confirm the commit. The artifact transitions to **`committed`**.

Verify from PowerShell:

```powershell
Invoke-RestMethod `
  -Uri "$env:AGIENCE_BASE_URL/artifacts/$artifactId" `
  -Headers @{ Authorization = "Bearer $env:AGIENCE_TOKEN" } `
  | Select-Object id, state
```

→ `state : committed`

### Scene 6 — Project to DKG (60s)

```powershell
agience-dkg wm-write `
  --from-agience-artifact $artifactId `
  --title "ADR: DKG v10 as Verifiable Memory Substrate" `
  --artifact-type "decision" `
  --context-graph-id $env:DKG_CONTEXT_GRAPH
```

Expected output (JSON):

```json
{
  "turn_uri": "agience://memory/agience-demo/...",
  "layer": "wm",
  "context_graph_id": "agience-demo",
  "status": "anchored",   // or "pending" if testnet RPC is down
  ...
}
```

Narrate while it runs: *"The CLI fetches the committed artifact from Agience, builds a typed `agience:` JSON-LD Knowledge Asset — `@type: agience:decision`, predicates for author, tags, collection, memory layer — attaches the commit receipt ID, and POSTs it through the DKG node's MCP transport."*

When it returns:

- If `status: anchored` → *"Anchored on-chain. The Knowledge Asset has a UAL and is SPARQL-queryable across Context Graphs."*
- If `status: pending` → *"MCP transport succeeded — the DKG node accepted the typed asset. Anchoring is pending because the public testnet RPC is intermittent. The integration distinguishes transport success from anchoring state honestly, rather than failing silently."*

### Scene 7 — Show the typed JSON-LD (45s)

Open `integration/package/src/agience_dkg_integration/client.py` to the `memory_turn` method. Highlight the JSON-LD construction:

```python
jsonld = {
    "@context": {"agience": "https://agience.ai/schema/"},
    "@type": f"agience:{request.artifact_type}",
    "agience:author": ...,
    "agience:tags": ...,
    "agience:collection": ...,
    "agience:memoryLayer": ...,
    "agience:commitReceiptId": commit_receipt_id,
}
```

Narrate: *"Not a generic `schema:Article`. The `agience:` vocabulary makes the asset type-aware — any agent can SPARQL-query for `?x a agience:decision` across organisations and get back governed, attested artifacts."*

### Scene 8 — Test suites (45s)

```powershell
cd C:\Users\manoj\Repos\agience\integration\package
pytest tests/unit -v --tb=no -q
```

→ *60 passed*

```bash
# in WSL, with DKG node running
DKG_BASE_URL=http://localhost:8083 \
DKG_TOKEN=53e0a288-1cd9-40de-b75c-1f53c4c77b05 \
DKG_CONTEXT_GRAPH=agience-test \
.venv/bin/pytest package/tests/integration -v -s
```

→ *5 passed* (the long blockchain-anchoring ones may take ~9 minutes — record the start, cut to the result, narrate the gap).

Narrate: *"60 unit tests cover the typed JSON-LD generation, governance gate refusal of drafts, MCP transport, error reporting, and CLI flow. 5 integration tests run end-to-end against the live DKG node on a real testnet."*

### Scene 9 — FLARE reference (30s, optional)

```bash
cd C:\Users\manoj\Repos\agience\flare-index
make test
```

→ *101 passed*

Narrate: *"FLARE is the cryptographic confidentiality layer. When an Agience collection is classified confidential, only derived projections reach DKG — raw content stays AES-256-GCM encrypted with per-cell keys from a Shamir-threshold oracle. The integration's policy model routes through FLARE when needed."*

### Scene 10 — Close (30s)

> "Three layers, one trust gradient. Agience for human-governed authoring. FLARE for cryptographic confidentiality. DKG v10 for shared verifiable memory. The integration is a thin, honest, typed bridge — and it refuses to cross the boundary unless a human has committed the artifact."
>
> "Submitted for the OriginTrail × Agience Flagship Round 1 bounty."

---

## Recording checklist

- [ ] Agience backend running, UI logged in
- [ ] DKG agent on `:8083`, `/health` returns 200
- [ ] `integration/package/.env` populated and verified
- [ ] Scene 4 produces the **governance refusal** error (this is the money shot — don't skip)
- [ ] Scene 6 produces a `turn_uri` and an explicit `status` field
- [ ] Unit test count is **60 passed**, integration tests **5 passed**
- [ ] No competitor submissions or unbounded speculation about Beacon
- [ ] Audio levels consistent across terminals and UI

## Common gotchas (and the fix)

| Symptom | Cause | Fix |
|---|---|---|
| `Governance error: ... draft, not committed` (when you expected committed) | Artifact was created in a **collection**, not a workspace, so the workspace commit didn't touch it. | Create the artifact via UI **inside a workspace** (Inbox is fine), or create directly via `POST /artifacts` with `container_id` = a workspace ID. |
| `Commit only supported on workspaces` | Trying to commit a collection ID. | Commit the parent **workspace** ID instead. |
| `307 Temporary Redirect` on `/mcp` | `DKG_BASE_URL` is pointing at the Agience backend (8081), not the DKG node. | Set `DKG_BASE_URL=http://localhost:8083` in `integration/package/.env`. |
| `401 Unauthorized` on `/mcp/` | Same as above. | Same as above. |
| `No LLM connection available. Set OPENAI_API_KEY ...` | Aria's chat handler can't see your OpenAI key. | Put `OPENAI_API_KEY=sk-...` in `agience-core/.env` (the UI LLM Keys tab does **not** wire into the default chat handler — flagged as a bug to John). |
| `missing required option(s): --title` after `--from-agience-artifact` | Artifact has no `title` (UI doesn't enforce it). | Pass `--title "..."` explicitly until Agience tightens validation. |
| Blockchain anchor returns `pending`, lofar-testnet error in DKG log | Public OT-node RPC intermittent. | Either retry, or accept `pending` — narrate it as the integration honestly reporting state. |
