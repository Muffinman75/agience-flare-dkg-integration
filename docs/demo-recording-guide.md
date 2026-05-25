# Demo Recording Guide — Agience × DKG v10 Integration

**Last updated:** 2026-05-23 (post-daemon-integration; v0.4.0)

This is the practical, scene-by-scene shooting script for the bounty submission video. It reflects the flow proved end-to-end on 2026-05-23 against the official OriginTrail v10 daemon: an OpenAI-powered LLM in Agience generates an Architecture Decision Record, a human commits it through Agience's governance boundary, and the integration projects it as a typed `agience:` Knowledge Asset directly into the local DKG v10 daemon — refusing to project anything still in `draft`.

> **🎥 Recording plan for v0.4.0 — single daemon demo.** Re-record Scenes 2 (services), 4 (governance refusal), 6 (successful daemon write), 7 (file reference: `daemon_client.py`), 8 (test count `75 passed`). Scenes 1, 3, 5, 9, 10 can be reused if their narration still aligns with the daemon-first framing.
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
npm install -g @origintrail-official/dkg
dkg init           # one-time; writes ~/.dkg/auth.token
DKG_PORT=9201 dkg start   # 9200 collides with Windows Elasticsearch; use 9201
```

Verify:

```bash
curl -s http://127.0.0.1:9201/health
# {"error":"Unauthorized — provide a valid Bearer token..."} confirms it's listening
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
DKG_CONTEXT_GRAPH=agience-demo
# DKG_DAEMON_TOKEN is auto-read from ~/.dkg/auth.token; only set explicitly if you've moved it

# Agience platform (for --from-agience-artifact)
AGIENCE_BASE_URL=http://localhost:8081
AGIENCE_TOKEN=agc_...
```

The `agience-dkg` CLI auto-loads this file at startup; shell exports still take precedence per-command. If you ever record the MCP transport, override `DKG_TRANSPORT=mcp`, `DKG_BASE_URL=http://localhost:8083`, and `DKG_TOKEN=<mcp-bearer>` per-invocation.

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

### Scene 2 — The three running services (30s)  🎥 **RE-RECORD**

Quick cuts through the three terminals:

- Agience backend log line: `Application startup complete.`
- DKG daemon: `dkg status` shows running, then `curl http://127.0.0.1:9201/health` returns the `401 Unauthorized` healthy-listening signal
- The Agience UI logged in, Inbox workspace visible

Narrate: *"Three components running locally: the Agience platform on 8081, the official OriginTrail DKG v10 daemon on 9201, and the integration CLI. No testnet RPC, no public node — the whole demo loop runs against the daemon OriginTrail just shipped."*

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

### Scene 4 — The governance gate refuses to project a draft (45s)  🎥 **RE-RECORD**

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
Governance error: Artifact '<id>' is in state 'draft', not 'committed'.
Only committed Agience artifacts may be projected to DKG.
```

Narrate: *"The integration refuses. This is the whole point: drafts cannot become shared memory. Governance is enforced at the boundary, not by policy. Same refusal whether the downstream is the local daemon or an MCP-fronted node — the gate is upstream of transport."*

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

### Scene 6 — Project to DKG (60s)  🎥 **RE-RECORD**

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

Expected output (real, captured 2026-05-23):

```json
{
  "turn_uri": "did:dkg:context-graph:agience-demo/assertion/0x6863…/<artifactId>-ADR-DKG-v10-as-Verifiable-Memory-Substrate",
  "layer": "wm",
  "context_graph_id": "agience-demo",
  "status": "anchored",
  "error": null,
  "raw_response": {
    "create": { "assertionUri": "did:dkg:context-graph:agience-demo/assertion/..." },
    "write":  { "written": 8 }
  }
}
```

Narrate while it runs: *"The CLI fetches the committed artifact from Agience, builds a typed `agience:` RDF Knowledge Asset — `agience:decision` as the type, predicates for author, tags, collection, memory layer — attaches the commit receipt ID, and POSTs it as quads through `daemon_client.py` to the local DKG v10 daemon: first `POST /api/assertion/create`, then `POST /api/assertion/<name>/write`. The MCP transport sends the same predicate set as JSON-LD — we'll see both side by side in Scene 7."*

When it returns: *"Anchored. Eight RDF quads written. The Knowledge Asset has a stable assertion URI under the Context Graph and is immediately SPARQL-queryable. No testnet RPC was involved — this is the daemon's own local store."*

### Scene 7 — Show the typed RDF (60s)  🎥 **RE-RECORD** (split view — both transports)

**Important:** the two transports encode the **same RDF predicates** but in different wire formats — MCP sends JSON-LD; the daemon sends N-Triples quads. Show both side by side so the "same predicates, different transport" claim is visible on screen. Split the editor vertically (VS Code: drag the tab to the right edge, or `Ctrl+\`).

**Left pane — `package/src/agience_dkg_integration/client.py`, around lines 158–182** (MCP transport, JSON-LD):

```python
jsonld: Dict[str, Any] = {
    "@context": {
        "schema": "https://schema.org/",
        "agience": "https://agience.ai/ontology/",
    },
    "@type": f"agience:{request.artifact_type or 'Artifact'}",
    "@id": f"agience:{request.context_graph_id}/{request.artifact_id or 'unknown'}",
    "schema:name": request.title or f"agience:{request.context_graph_id}",
    "schema:text": request.markdown,
    "agience:contextGraphId": request.context_graph_id,
    "agience:memoryLayer": request.layer,
    "agience:artifactId": request.artifact_id or "",
}
if request.author:
    jsonld["agience:author"] = request.author
if request.tags:
    jsonld["agience:tags"] = request.tags
if request.collection_id:
    jsonld["agience:collection"] = request.collection_id
if request.commit_receipt_id:
    jsonld["agience:commitReceiptId"] = request.commit_receipt_id
```

**Right pane — `package/src/agience_dkg_integration/daemon_client.py`, around lines 159–236** (daemon transport, quads built by `_quads_for_artifact`):

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

Narrate: *"Two transports, one RDF model. On the left, the MCP path sends JSON-LD — `@type: agience:decision`, plus the typed `agience:` predicates. On the right, the daemon path sends the equivalent N-Triples quads to `/api/assertion/create` and `/api/assertion/{name}/write`. Same `agience:` namespace, same predicate set, same SPARQL-queryable shape on the other side — only the wire format differs. Not a generic `schema:Article`: any agent can SPARQL-query for `?x a agience:decision` across organisations and get back governed, attested artifacts."*

> If a single-pane shot is preferred for the live pitch clip, show **just the daemon side** (`_quads_for_artifact`) since that's what the demo actually exercises in Scene 6, and use the JSON-LD `demo-jsonld.json` `cat` shot (per `demo-clip-script.md` Scene 3) as the conceptual payload representation.

### Scene 8 — Test suites (45s)  🎥 **RE-RECORD** (counts changed)

```bash
cd /mnt/c/Users/manoj/Repos/agience/integration
source .venv/bin/activate
python -m pytest package/tests/unit -q
```

→ *75 passed* (15 of which are new daemon-client coverage: token resolution priority, WM write, SWM write, promote, SPARQL with `GRAPH ?g` named-sub-graph traversal)

```bash
# Integration tests (requires either the daemon on :9201 or an MCP node on :8081/:8083)
DKG_BASE_URL=http://127.0.0.1:9201 DKG_CONTEXT_GRAPH=agience-test \
  python -m pytest package/tests/integration -v -s
```

→ *5 passed*

Narrate: *"75 unit tests cover both transports, the governance gate refusal of drafts, typed JSON-LD generation, error reporting, and the CLI flow. 5 integration tests run end-to-end against a live DKG v10 daemon — or an MCP-fronted node — with identical results."*

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
- [ ] DKG v10 daemon running on `:9201` (`dkg status` confirms; `curl /health` returns 401 without token)
- [ ] `integration/package/.env` populated; `WIN_HOST` resolved if recording from WSL
- [ ] Scene 4 produces the **governance refusal** error (this is the money shot — don't skip)
- [ ] Scene 6 produces a `turn_uri` and `status: anchored` against the daemon
- [ ] Unit test count is **75 passed**, integration tests **5 passed**
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
| `Address already in use` on port 9200 | Windows Elasticsearch holds 9200. | Use `DKG_PORT=9201 dkg start` (already the default in this guide). |
| `No LLM connection available. Set OPENAI_API_KEY ...` | Aria's chat handler can't see your OpenAI key. | Put `OPENAI_API_KEY=sk-...` in `agience-core/.env` (the UI LLM Keys tab does **not** wire into the default chat handler — flagged as a bug to John). |
| `missing required option(s): --title` after `--from-agience-artifact` | Artifact has no `title` (UI doesn't enforce it). | Pass `--title "..."` explicitly until Agience tightens validation. |
| Blockchain anchor returns `pending`, lofar-testnet error in DKG log | Public OT-node RPC intermittent. | Either retry, or accept `pending` — narrate it as the integration honestly reporting state. |
