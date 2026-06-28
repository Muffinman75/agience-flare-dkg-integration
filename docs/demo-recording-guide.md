# Demo Recording Guide — Agience × DKG v10 Integration

**Last updated:** 2026-06-28 (DKG v10.0.1; v0.4.2; Node UI walkthrough + testnet context graph registration)

> **Fork note.** All `agience-core` and `flare-index` changes shown in this guide (DKG projection read model, the `DkgProjectionPanel` UI, projection/publication endpoints) live on the author's forks at [github.com/Muffinman75](https://github.com/Muffinman75), not the upstream `Agience/*` repos. Check out the forks to reproduce the UI and backend behaviour described here.

This is the practical, scene-by-scene shooting script for the bounty submission video. It reflects the flow proved end-to-end on 2026-05-23 against the official OriginTrail v10 daemon: an OpenAI-powered LLM in Agience generates an Architecture Decision Record, a human commits it through Agience's governance boundary, and the integration projects it as a typed `agience:` Knowledge Asset directly into the local DKG v10 daemon — refusing to project anything still in `draft`.

> **🎥 Recording plan for v0.4.2 — single daemon demo.** Re-record Scenes 2 (services), 4 (governance refusal), 6 (successful daemon write + Node UI), 6A (UI Promote to Shared Memory + Node UI), 6B (search read-back + Node UI), 7 (optional single-pane `daemon_client.py`), 8 (test count `82 passed`). Scenes 1, 3, 5, 9, 10 can be reused if their narration still aligns with the daemon-first framing.
>
> **MCP transport is supported on the same code path** (`--transport mcp`, see Scene 7 narration and the README). Reviewers can exercise it themselves by pointing `DKG_BASE_URL` at an MCP-fronted DKG node once their side is reachable — no separate video is recorded, because the governance gate, JSON-LD payload shape, and CLI surface are transport-independent. This mirrors RepNet's single-flow recording posture.

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

### 0.2 DKG v10 daemon (canonical)

Install and start the official OriginTrail v10 daemon in WSL:

```bash
npm install -g @origintrail-official/dkg   # v10.0.1+
dkg init           # one-time; writes ~/.dkg/auth.token
```

The daemon must bind to `0.0.0.0` so the Node UI is reachable from Windows Chrome (WSL2's `localhost` is not Windows `localhost`). Edit `~/.dkg/config.json`:

```bash
python3 - <<'PY'
import json
with open('/home/manoj/.dkg/config.json', 'r') as f:
    cfg = json.load(f)
cfg['apiHost'] = '0.0.0.0'
with open('/home/manoj/.dkg/config.json', 'w') as f:
    json.dump(cfg, f, indent=2)
PY
```

Then start on port 9201 (9200 collides with Windows Elasticsearch):

```bash
DKG_PORT=9201 dkg start
```

> **rc.17 one-time upgrade (do once, before the first start).** rc.17 redeploys contracts and changes the local graph storage layout, so do the one-time store wipe per [`UPGRADE_TO_RC17`](https://github.com/OriginTrail/dkg/blob/main/docs/UPGRADE_TO_RC17.md) (wallet/identity/on-chain assets are safe). On first start the daemon also downloads an **Oxigraph** binary into `~/.dkg/oxigraph/`. If your network blocks that download the daemon **appears to hang on boot with no error** — pre-seed it: download the matching `oxigraph-vX.Y.Z` executable, verify its SHA-256, and drop it into `~/.dkg/oxigraph/` before `dkg start`. (Reference values used on this machine: `oxigraph-v0.5.8.exe`, SHA-256 `9c847300f440e4571a41957d9f9d54272a52baa703b27267a1ab0ede2ca513f6`.)

Verify it's listening inside WSL2:

```bash
curl -s http://127.0.0.1:9201/health
# {"error":"Unauthorized — provide a valid Bearer token..."} confirms it's listening
ss -tlnp | grep 9201
# should show 0.0.0.0:9201
```

Create the demo context graph if it doesn't exist:

```bash
dkg context-graph create agience-demo
# Note the canonical ID returned, e.g. 0x9dbC922D52507b06e16917C83f9AB436fEac8a73/agience-demo
```

The daemon is the **primary transport** for the demo. WM writes are fully local — no testnet RPC required.

### 0.2b (Optional) MCP-fronted DKG agent

Only if you also want to record the MCP transport path. File: `dkg/dkg-node/apps/agent/.env`. Set `PORT=8083` (8081 collides with Agience backend) and leave the existing `DKG_OTNODE_URL` / wallet values alone.

### 0.3 Integration package `.env`

File: `integration/package/.env`

Copy from the template and set:

```
# Primary transport (daemon)
DKG_TRANSPORT=daemon
DKG_BASE_URL=http://127.0.0.1:9201
# Use the canonical ID returned by `dkg context-graph create`, e.g.:
DKG_CONTEXT_GRAPH=0x9dbC922D52507b06e16917C83f9AB436fEac8a73/agience-demo
# DKG_DAEMON_TOKEN is auto-read from ~/.dkg/auth.token; only set explicitly if you've moved it

# Agience platform (for --from-agience-artifact)
# Reviewers (recommended): use the hosted SaaS instead of a local stack:
#   AGIENCE_BASE_URL=https://my.agience.ai
AGIENCE_BASE_URL=http://localhost:8081
AGIENCE_TOKEN=agc_...
```

The `agience-dkg` CLI auto-loads this file at startup; shell exports still take precedence per-command. If you ever record the MCP transport, override `DKG_TRANSPORT=mcp`, `DKG_BASE_URL=http://localhost:8083`, and `DKG_TOKEN=<mcp-bearer>` per-invocation.

To open the DKG Node UI from Windows, use the WSL2 IP (not `localhost`):

```bash
hostname -I
# → http://<first-ip>:9201/ui
```

### 0.4 Reinstall the package (only after pulling new code)

```powershell
cd C:\Users\manoj\Repos\agience\integration\package
pip install -e .
```

This picks up the new `python-dotenv` dependency and the auto-loader.

---

## 1. Start the three services (per recording session)

Open three terminals.

### Terminal 1 — Agience backend

```powershell
cd C:\Users\manoj\Repos\agience\agience-core
.\agience.bat dev
```

Wait until the backend logs `Application startup complete.` Open the UI at `http://localhost:5173` and log in.

### Terminal 2 — DKG v10 daemon (WSL)

```bash
DKG_PORT=9201 dkg start
```

If already running, confirm:

```bash
dkg status   # or: curl -s http://127.0.0.1:9201/health
```

A `401 Unauthorized` from `/health` (without a token) is the healthy signal that the daemon is listening.

### Terminal 3 — recording terminal (WSL, **recommended** — avoids PowerShell quoting issues and `localhost`-vs-Windows-host confusion)

```bash
cd /mnt/c/Users/manoj/Repos/agience/integration
source .venv/bin/activate

# Load .env (handles inline comments and CRLF safely)
eval "$(python -c 'from dotenv import dotenv_values; [print(f\"export {k}={v!r}\") for k,v in dotenv_values(\"package/.env\").items() if v]')"

# WSL → Windows host: localhost in WSL2 is NOT the Agience host. Resolve once:
WIN_HOST=$(ip route show | awk '/default/ {print $3}')
AGIENCE_BASE_URL="http://$WIN_HOST:8081"  # override the .env's localhost
```

Verify:

```bash
echo "DKG_BASE_URL=$DKG_BASE_URL"
echo "AGIENCE_BASE_URL=$AGIENCE_BASE_URL"
agience-dkg wm-write --help | head
```

> **Invocation block.** Every `wm-write` call prints a `# agience-dkg wm-write — resolved invocation (copy to replay):` block to stdout before the HTTP call fires. It shows the fully-resolved flags (transport, base-url, agience-base-url, etc.) with tokens truncated to 8 chars. Testers and reviewers can copy it directly from the terminal or any captured log to replay the exact call.

---

## 2. Recording — scene by scene

Total target length: **5–6 minutes** — per OriginTrail's guidance (FamousAmos, 17 Jun: *"5/6 mins would be perfect; 10 mins may be a bit too long"*). Tight, focused, no dead air.

**Shot budget (the 5–6 minute submission cut).** The per-scene parenthetical times in the headings below are the *long-cut* originals — use this table for the submission cut. Deliver narration briskly and cut to the next scene the moment a command returns.

| Scene | Cut | Budget |
|---|---|---|
| 1 — Why this exists | keep (trim) | 0:40 |
| 2 — Three services | keep (quick cuts) | 0:15 |
| 3 — Agent deposits draft (Scene 3A folded in as one sentence) | keep | 0:45 |
| 4 — Governance refusal *(money shot)* | keep | 0:30 |
| 5 — Human commit | keep | 0:30 |
| 6 — Project to DKG WM (CLI + Node UI) | keep | 0:45 |
| 6A — SHARE → Shared Memory (UI Promote + Node UI) | keep | 0:30 |
| 6B — Read it back via search (CLI + Node UI) | keep | 0:30 |
| 7 — Typed RDF (optional, single-pane code) | keep if time | 0:10 |
| 8 + 9 — Tests + FLARE | **combine**, show counts only (82 / 5 / 101) | 0:25 |
| 10 — Close | keep | 0:20 |
| **Total** | | **≈ 5:35** |

**Scene 3A is folded into Scene 3** as a single sentence — no separate segment. If you overrun, the first things to drop are Scene 1 detail and the optional Scene 7 code shot. **Never drop Scene 4** (the governance refusal) or **Scenes 6A/6B** (the Shared-Memory write→read loop, which is the round's actual scope).

### Scene 1 — Why this exists (0:40, slide / talking head)

> "Enterprise AI has a memory problem. LLMs generate at scale, but the output has no identity, provenance, or chain of custody. Two agents can't even agree on what their team decided yesterday."
>
> "Agience governs the human side: every artifact is typed, versioned, and crosses an explicit commit boundary. OriginTrail DKG v10 handles the cross-organisation side: a verifiable knowledge graph anyone can query."
>
> "This integration bridges them. Only committed Agience artifacts reach DKG — as typed `agience:` Knowledge Assets with receipts linking on-chain records back to human-approved versions."

Show the architecture diagram from `integration/DESIGN_BRIEF.md` if you have one ready.

### Scene 2 — The three running services (0:15)  🎥 **RE-RECORD**

Quick cuts through the three services:

- Agience backend log line: `Application startup complete.`
- DKG daemon: `dkg status` shows running, `ss -tlnp | grep 9201` shows `0.0.0.0:9201`, and the Node UI is open in Chrome at `http://<WSL2_IP>:9201/ui`
- The Agience UI logged in, Inbox workspace visible

Narrate: *"Three services: Agience platform on 8081, OriginTrail DKG v10 daemon on 9201, the integration CLI. No testnet RPC — everything runs against the daemon OriginTrail just shipped. The daemon is inside WSL2 but its UI is exposed to Windows so we can show the graph live."*

### Scene 3 — Agent deposits an artifact into Agience via MCP (0:45)

In the Agience UI, navigate to the **Inbox** workspace. Open the chat / "Ask anything" surface. Paste:

```
Write an architecture decision record for using DKG v10 as a shared
verifiable memory substrate for multi-agent AI systems. Include:
context, decision, rationale, and consequences. Under 300 words.
Format as Markdown.
```

Press send. Wait for Aria's tool calls to land. A new **draft** artifact appears in the workspace with the ADR content.

Narrate: *"Any MCP-capable agent — OpenClaw, Hermes, Claude Code — deposits into Agience via the `create_artifact` tool. This is framework-agnostic ingestion: Agience doesn't care which agent wrote it, only whether a human committed it. The result is a typed artifact in the workspace, but it's still a `draft`. Nothing has crossed the trust boundary yet."*

Click into the new artifact. Show its state in the right-hand panel: **`draft`**.

### Scene 4 — The governance gate refuses to project a draft (0:30)  🎥 **RE-RECORD**

Cut to Terminal 3. Grab the draft artifact's ID from the URL or backend log:

```bash
artifactId="<the-draft-artifact-id>"
```

Run against the daemon:

```bash
agience-dkg wm-write \
  --transport daemon \
  --from-agience-artifact "$artifactId" \
  --title "ADR: DKG v10 as Verifiable Memory Substrate" \
  --artifact-type "decision" \
  --context-graph-id "$DKG_CONTEXT_GRAPH" \
  --base-url "$DKG_BASE_URL" \
  --agience-base-url "$AGIENCE_BASE_URL" \
  --agience-token "$AGIENCE_TOKEN"
```

Expected output:

```
# agience-dkg wm-write — resolved invocation (copy to replay):
agience-dkg wm-write \
  --transport daemon \
  --from-agience-artifact "<the-draft-artifact-id>" \
  --title "ADR: DKG v10 as Verifiable Memory Substrate" \
  --artifact-type "decision" \
  --context-graph-id "agience-demo" \
  --base-url "http://127.0.0.1:9201" \
  --token "53e0a28..." \
  --agience-base-url "http://<WIN_HOST>:8081" \
  --agience-token "(env)"
Governance error: Artifact '<id>' is in state 'draft', not 'committed'.
Only committed Agience artifacts may be projected to DKG.
```

Narrate: *"The integration refuses. Drafts cannot become shared memory. Governance is enforced at the boundary, not by policy. Same refusal whether downstream is local daemon or MCP node — the gate is upstream of transport."*

### Scene 5 — Human commit (0:30)

Back in the UI. Click **Commit** on the workspace. The Commit Preview dialog opens, listing the draft and its target collection.

Narrate: *"The commit preview is the human-review gate. It surfaces what's about to become governed and where it's going. Confirm — artifact transitions to `committed`. Verify via API: state is now `committed`."*

Verify from PowerShell:

```powershell
Invoke-RestMethod `
  -Uri "$env:AGIENCE_BASE_URL/artifacts/$artifactId" `
  -Headers @{ Authorization = "Bearer $env:AGIENCE_TOKEN" } `
  | Select-Object id, state
```

→ `state : committed`

### Scene 6 — Project to DKG (0:45)  🎥 **RE-RECORD**

Same command as Scene 4 — except the artifact is now `committed`, so the gate lets it through:

```bash
agience-dkg wm-write \
  --transport daemon \
  --from-agience-artifact "$artifactId" \
  --title "ADR: DKG v10 as Verifiable Memory Substrate" \
  --artifact-type "decision" \
  --context-graph-id "$DKG_CONTEXT_GRAPH" \
  --base-url "$DKG_BASE_URL" \
  --agience-base-url "$AGIENCE_BASE_URL" \
  --agience-token "$AGIENCE_TOKEN"
```

Expected output (real, captured 2026-06-27):

```
# agience-dkg wm-write — resolved invocation (copy to replay):
agience-dkg wm-write \
  --transport daemon \
  --from-agience-artifact "<artifactId>" \
  --title "ADR: DKG v10 as Verifiable Memory Substrate" \
  --artifact-type "decision" \
  --context-graph-id "0x9dbC922D52507b06e16917C83f9AB436fEac8a73/agience-demo" \
  --base-url "http://127.0.0.1:9201" \
  --token "(env/file)" \
  --agience-base-url "http://<WIN_HOST>:8081" \
  --agience-token "(env)"
```

```json
{
  "turn_uri": "did:dkg:context-graph:0x9dbC922D52507b06e16917C83f9AB436fEac8a73/agience-demo/_working_memory/0x9dbC922D52507b06e16917C83f9AB436fEac8a73/0",
  "layer": "wm",
  "context_graph_id": "0x9dbC922D52507b06e16917C83f9AB436fEac8a73/agience-demo",
  "status": "anchored",
  "error": null,
  "raw_response": {
    "knowledgeAsset": {
      "name": "<artifactId>-ADR-DKG-v10-as-Verifiable-Memory-Substrate",
      "assertionUri": "did:dkg:context-graph:0x9dbC922D52507b06e16917C83f9AB436fEac8a73/agience-demo/_working_memory/0x9dbC922D52507b06e16917C83f9AB436fEac8a73/0",
      "alreadyExists": false,
      "status": "draft-open",
      "written": 8
    }
  }
}
```

> v10.0.1: this is a single atomic `POST /api/knowledge-assets` (create + write of an unsealed WM draft, `finalize:false`). On a pre-v10.0.1 daemon the client transparently falls back to the legacy two-call `POST /api/assertion/create` + `POST /api/assertion/{name}/write` and the `raw_response` shows the `create`/`write` pair instead. The `Note: DKG write succeeded but recording it back to Agience failed...` line is a best-effort write-back to the Agience projection panel; it does not affect the DKG write.

Narrate while it runs: *"The CLI fetches from Agience, builds a typed `agience:` RDF Knowledge Asset, and POSTs it to the local DKG v10 daemon. On v10.0.1 that's one atomic call to `POST /api/knowledge-assets`."*

When it returns: *"Anchored — eight quads written, stable UAL, immediately SPARQL-queryable. No testnet RPC involved."*

**Cut to the Node UI** at `http://<WSL2_IP>:9201/ui`. Navigate to the `agience-demo` context graph → **Working Memory** tab. The just-written Knowledge Asset appears as a single entity with 8 triples. This is the visual proof that the Agience artifact is now a DKG Knowledge Asset in WM.

### Scene 6A — SHARE to Shared Memory (0:30)  🎥 **NEW** (the second half of the round's scope)

This scene makes the **Shared Memory** layer visible — until now the demo only showed Working Memory. SHARE is the Curator-authorized promotion from WM → SWM. Because the Node UI is now live, perform the promotion **in the UI**; the CLI remains the exact same call underneath.

**In the Node UI** at `http://<WSL2_IP>:9201/ui`:

1. Stay on the `agience-demo` context graph → **Working Memory** tab.
2. The ADR entity from Scene 6 is shown (1 entity, 8 triples).
3. Click the **Promote** button on the ADR entity (or use the **Promote All** control).
4. Confirm the promotion in the UI.

Representative CLI equivalent (run in the background if the UI promotion fails, or show it as the underlying API call):

```bash
# KA name = <artifactId>-<title-slug>
kaName="${artifactId}-ADR-DKG-v10-as-Verifiable-Memory-Substrate"

agience-dkg promote "$kaName" \
  --transport daemon \
  --context-graph-id "$DKG_CONTEXT_GRAPH" \
  --base-url "$DKG_BASE_URL" \
  --from-agience-artifact "$artifactId" \
  --agience-base-url "$AGIENCE_BASE_URL" \
  --agience-token "$AGIENCE_TOKEN"
```

Representative output if you verify via CLI:

```json
{
  "ok": true,
  "name": "<artifactId>-ADR-DKG-v10-as-Verifiable-Memory-Substrate",
  "raw_response": {
    "contextGraphId": "0x9dbC922D52507b06e16917C83f9AB436fEac8a73/agience-demo",
    "status": "shared"
  }
}
```

> v10.0.1: the UI Promote action calls the same `POST /api/knowledge-assets/{name}/swm/share` (the rename of `promote`) that the CLI uses. It is **explicit and Curator-authorized — never automatic** (bounty §6, §7). The optional `--from-agience-artifact` CLI flag records the SWM stage back onto the Agience artifact's DKG Projection panel (best-effort); if you promote in the UI, this best-effort Agience write-back is skipped, so the DKG graph remains the authoritative record.

Narrate: *"SHARE is the deliberate, Curator-authorized promotion from Working Memory to Shared Memory — the team-gossiped layer. Nothing shares silently. I click Promote in the DKG Node UI; the same stable UAL carries up — no re-IDing — keeping the path to Verifiable Memory a promotion, not a rewrite."*

**Cut to the Shared Working Memory tab** in the Node UI. The promoted ADR now appears there (still 1 entity, 8 triples, now labeled as shared). This is the visual proof that the Curator-authorized promotion moved the artifact across the trust gradient.

### Scene 6B — Read it back across the team (0:30)  🎥 **NEW** (closes the read/write loop)

This is the payoff: a *different* agent (or teammate) finds the just-shared artifact by querying Shared Memory — the LLM-Wiki "retrieval and writing in one loop."

```bash
agience-dkg search "verifiable memory substrate" \
  --transport daemon \
  --context-graph-id "$DKG_CONTEXT_GRAPH" \
  --layers swm \
  --base-url "$DKG_BASE_URL"
```

Representative output (`MemorySearchResult`; capture live on the day):

```json
{
  "result_count": 1,
  "results": [
    {
      "s": "https://agience.ai/ontology/agience-demo/<artifactId>",
      "name": "ADR: DKG v10 as Verifiable Memory Substrate",
      "text": "## Context ... ## Decision ... ## Consequences ...",
      "memoryLayer": "wm",
      "artifactId": "<artifactId>",
      "author": "Aria",
      "collection": "<collection-id>"
    }
  ]
}
```

> The query runs a SPARQL `SELECT` over `GRAPH ?g { … }` against `POST /api/query`, scoped to the Context Graph **inside** the SPARQL via `CONTAINS(STR(?s), cgId)`. (v10.0.1 note: the `contextGraphId` body field scopes `/api/query` to a meta-only view that excludes the `_shared_memory` / `_working_memory` content graphs, so the client deliberately omits it — see `daemon_client.py:memory_search`.) The `agience:` predicates make the row typed and attributable, not free text.

Narrate: *"A teammate's agent queries Shared Memory and gets back a typed, attributed Knowledge Asset: author, collection, memory layer, full text — all under the `agience:` vocabulary. Write on one side, read on the other. That's the shared memory substrate the round is about."*

**Cut to the Node UI** → `agience-demo` context graph → **Shared Working Memory** tab. The same ADR entity is visible there, confirming the read-back query is operating over the actual shared graph. This closes the write → promote → read loop visually, not just in JSON.

### Scene 7 — Show the typed RDF (0:10, optional)  🎥 **RE-RECORD** (single-pane, daemon side only)

The Node UI in Scenes 6–6B proves the KA exists. This scene briefly shows *why* the query works: the daemon writes typed `agience:` quads, not an untyped blob.

**Single pane — `package/src/agience_dkg_integration/daemon_client.py`, around lines 159–236** (`_quads_for_artifact`):

```python
quads: List[Dict[str, str]] = [
    {"subject": subject_uri, "predicate": _RDF_TYPE, "object": type_uri},
    {"subject": subject_uri, "predicate": f"{_SCHEMA_NS}name",          "object": _lit(request.title or request.context_graph_id)},
    {"subject": subject_uri, "predicate": f"{_SCHEMA_NS}text",          "object": _lit(request.markdown)},
    {"subject": subject_uri, "predicate": f"{_AGIENCE_NS}contextGraphId", "object": _lit(request.context_graph_id)},
    {"subject": subject_uri, "predicate": f"{_AGIENCE_NS}memoryLayer",  "object": _lit(request.layer)},
]
# ... agience:author, agience:tags, agience:collection, agience:commitReceiptId etc. conditionally appended below
```

Narrate: *"Same `agience:` namespace and predicate set, whether the wire is N-Triples or JSON-LD. Agents query for `agience:decision` and get governed, attested artifacts — not generic text."*

### Scene 8 — Test suites (0:15)  🎥 **RE-RECORD** (counts changed)

```bash
cd /mnt/c/Users/manoj/Repos/agience/integration
source .venv/bin/activate
python -m pytest package/tests/unit -q
```

→ *82 passed* (daemon-client coverage includes token resolution priority, WM write, SWM write, promote/share, the v10.0.1 `/api/knowledge-assets` surface + one-time `404` legacy fallback, `vm_publish`, and SPARQL with `GRAPH ?g` named-sub-graph traversal)

```bash
# Integration tests (requires either the daemon on :9201 or an MCP node on :8081/:8083)
DKG_BASE_URL=http://127.0.0.1:9201 DKG_CONTEXT_GRAPH=agience-test \
  python -m pytest package/tests/integration -v -s
```

→ *5 passed*

Narrate: *"Eighty-two unit tests cover both transports, the governance gate, v10.0.1 surface with legacy fallback, Verifiable Memory publish, and SPARQL traversal. Five integration tests run end-to-end against the daemon."*

### Scene 9 — FLARE reference (0:10, optional)

```bash
cd C:\Users\manoj\Repos\agience\flare-index
make test
```

→ *101 passed*

Narrate: *"FLARE is the cryptographic confidentiality layer — one-oh-one tests. When collections are confidential, only derived projections reach DKG; raw content stays encrypted."*

### Scene 10 — Close (0:20)

> "Three layers, one trust gradient. Agience for human-governed authoring. FLARE for cryptographic confidentiality. DKG v10 for shared verifiable memory. The integration is a thin, honest, typed bridge — and it refuses to cross the boundary unless a human has committed the artifact."
>
> "Submitted for the OriginTrail × Agience Flagship Round 1 bounty."

---

## Recording checklist

- [ ] Agience backend running, UI logged in
- [ ] DKG v10 daemon running on `:9201` (`dkg status` confirms; `curl /health` returns 401 without token; `ss` shows `0.0.0.0:9201`)
- [ ] `integration/package/.env` populated with the canonical `DKG_CONTEXT_GRAPH`; `WIN_HOST` resolved if recording from WSL
- [ ] Scene 4 produces the **governance refusal** error (this is the money shot — don't skip)
- [ ] Invocation block prints above the result in both Scene 4 and Scene 6 — confirm transport, base-url, and agience-base-url resolve correctly before the HTTP call fires
- [ ] Scene 6 produces a `turn_uri` and `status: anchored` against the daemon
- [ ] Node UI shows the new Knowledge Asset in **Working Memory** for `agience-demo`
- [ ] Node UI shows the promoted ADR in **Shared Working Memory** after Scene 6A
- [ ] Unit test count is **82 passed**, integration tests **5 passed**
- [ ] No competitor submissions or unbounded speculation about Beacon
- [ ] Audio levels consistent across terminals and UI

## Common gotchas (and the fix)

| Symptom | Cause | Fix |
|---|---|---|
| `Governance error: ... draft, not committed` (when you expected committed) | Artifact was created in a **collection**, not a workspace, so the workspace commit didn't touch it. | Create the artifact via UI **inside a workspace** (Inbox is fine), or create directly via `POST /artifacts` with `container_id` = a workspace ID. |
| `Commit only supported on workspaces` | Trying to commit a collection ID. | Commit the parent **workspace** ID instead. |
| `307 Temporary Redirect` on `/mcp` (MCP transport only) | `DKG_BASE_URL` is pointing at the Agience backend (8081), not the DKG node. | Set `DKG_BASE_URL=http://localhost:8083` and `DKG_TRANSPORT=mcp`. |
| `401 Unauthorized` on `/mcp/` (MCP transport only) | Same as above. | Same as above. |
| `401 Unauthorized` on `/api/...` (daemon transport) | Bearer token missing or stale. | Confirm `~/.dkg/auth.token` exists and is current; or set `DKG_DAEMON_TOKEN` explicitly. |
| `Connection refused` on `AGIENCE_BASE_URL=http://localhost:8081` from WSL | WSL2's `localhost` is not the Windows host. | `WIN_HOST=$(ip route show \| awk '/default/ {print $3}'); AGIENCE_BASE_URL="http://$WIN_HOST:8081"`. |
| Invocation block shows `--agience-base-url "http://localhost:8081"` when running from WSL | The `.env` value is read before the `WIN_HOST` override is applied. | Check the block *before* the HTTP call — if it still shows `localhost`, re-export `AGIENCE_BASE_URL` and re-run. The block will then show the corrected host. |
| `Address already in use` on port 9200 | Windows Elasticsearch holds 9200. | Use `DKG_PORT=9201 dkg start` (already the default in this guide). |
| `No LLM connection available. Set OPENAI_API_KEY ...` | Aria's chat handler can't see your OpenAI key. | Put `OPENAI_API_KEY=sk-...` in `agience-core/.env` (the UI LLM Keys tab does **not** wire into the default chat handler — flagged as a bug to John). |
| `missing required option(s): --title` after `--from-agience-artifact` | Artifact has no `title` (UI doesn't enforce it). | Pass `--title "..."` explicitly until Agience tightens validation. |
| Blockchain anchor returns `pending`, lofar-testnet error in DKG log | Public OT-node RPC intermittent. | Either retry, or accept `pending` — narrate it as the integration honestly reporting state. |
| `CONTEXT_GRAPH_NOT_FOUND` on `wm-write` | The context graph ID was not created in the daemon. | Run `dkg context-graph create agience-demo` and use the canonical ID it returns in `DKG_CONTEXT_GRAPH`. |
| Node UI at `localhost:9201/ui` returns `ERR_EMPTY_RESPONSE` from Windows | Daemon binds to `127.0.0.1` inside WSL2 by default. | Set `apiHost: "0.0.0.0"` in `~/.dkg/config.json`, restart, then open `http://<WSL2_IP>:9201/ui`. See §0.2. |
| `Resource temporarily unavailable` on `/home/manoj/.dkg/oxigraph-data/LOCK` | A previous Oxigraph or `dkg` process is still running. | `pkill -f oxigraph; pkill -f dkg; rm -f ~/.dkg/oxigraph-data/LOCK`, then `dkg start`. |
| Daemon **hangs on `dkg start`** with no error, never binds `:9201` | First-run Oxigraph binary download is blocked/stalled by the network. | Pre-seed `~/.dkg/oxigraph/oxigraph-vX.Y.Z` manually (verify SHA-256), then restart. See §0.2. |
| `404` on `/api/knowledge-assets`, or stale graph data after upgrade | Daemon predates v10.0.1, or the v10.0.1 one-time store wipe wasn't done. | The client auto-falls back to legacy `/api/assertion/*` on `404`; for v10.0.1 do the one-time store wipe per `UPGRADE_TO_RC17`. |
| `NO_DATA_IN_SWM` on `vm-publish` | Publishing to a **public** Context Graph (access-policy 0) — known daemon bug #1124. | Use a **private** Context Graph (access-policy 1) for VM publish/smoke tests. |
