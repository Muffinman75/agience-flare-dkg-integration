"""Direct HTTP client for the official OriginTrail DKG v10 daemon.

Talks to the daemon's local HTTP API (default ``http://127.0.0.1:9201``).

As of DKG ``v10.0.0-rc.17`` the daemon retired the ``/api/assertion/*`` routes
in favour of the unified, GitHub-shaped Knowledge Asset surface (OT-RFC-43):

* ``POST /api/knowledge-assets``                       — create KA + open WM draft
  (atomic: also writes quads, with optional ``finalize``/``alsoShareSwm``/``alsoPublishVm``)
* ``POST /api/knowledge-assets/{name}/wm/write``       — append quads to the draft
* ``POST /api/knowledge-assets/{name}/swm/share``      — Curator-authorized SHARE (was ``promote``)
* ``POST /api/knowledge-assets/{name}/vm/publish``     — mint/update on chain (Verifiable Memory)
* ``POST /api/shared-memory/write``                    — write directly to SWM (unchanged)
* ``POST /api/query``                                  — SPARQL SELECT (unchanged)
* ``GET  /api/status``                                 — health probe (unchanged)

The client defaults to the new ``/api/knowledge-assets`` surface and, if a route
returns ``404`` (a pre-rc.17 daemon where it does not yet exist), transparently
falls back **once** to the legacy ``/api/assertion/*`` routes and caches that
decision — so the same code works against rc.16 and rc.17 daemons alike.

This is the right path for governed authoring → DKG projection because:

1. WM writes do **not** require an on-chain publish — the assertion stays on
   the operator's daemon until ``promote`` is called explicitly.
2. SWM writes accept ``localOnly: true``, which keeps quads on the local node
   while exposing the same JSON shape an on-chain publish would return.
3. There is no dependency on the public Pegasus gateway nodes (which are
   currently behind HTTP authentication and do not accept unauthenticated
   v10 publish traffic during Round 1 of the bounty).

The class deliberately mirrors ``DkgHttpClient`` so callers (CLI, MCP server)
can swap transports through a single ``DKG_TRANSPORT`` env var without
otherwise touching their code.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from .models import (
    AssertionPromoteRequest,
    AssertionPromoteResult,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryTurnRequest,
    MemoryTurnResult,
)

_AGIENCE_NS = "https://agience.ai/ontology/"
_SCHEMA_NS = "https://schema.org/"
_RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

_NAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_assertion_name(*parts: str) -> str:
    """Return a stable, URL-safe assertion name from arbitrary parts.

    The daemon URL-encodes these for us, but a slug is friendlier in logs
    and keeps the path short.
    """
    raw = "-".join(p for p in parts if p)
    slug = _NAME_SAFE_RE.sub("-", raw).strip("-")
    return slug or "agience-artifact"


def _lit(value: str) -> str:
    """Encode a Python string as an N-Triples-style RDF literal.

    The daemon's quad endpoint accepts the raw object string, so we wrap the
    value in quotes and escape control characters to keep the parser happy.
    """
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _resolve_token(explicit: Optional[str]) -> str:
    """Resolve the daemon bearer token.

    Priority (so the daemon never mistakenly uses an MCP-flavour token):

    1. ``explicit`` argument
    2. ``DKG_DAEMON_TOKEN`` env var (daemon-specific override)
    3. ``~/.dkg/auth.token`` (created by ``dkg init``)
    4. ``DKG_TOKEN`` env var (last-resort fallback for non-standard layouts)
    """
    if explicit:
        return explicit
    daemon_env = os.environ.get("DKG_DAEMON_TOKEN")
    if daemon_env:
        return daemon_env
    token_path = Path.home() / ".dkg" / "auth.token"
    if token_path.is_file():
        for line in token_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped
    fallback = os.environ.get("DKG_TOKEN")
    return fallback or ""


class DkgDaemonClient:
    """Synchronous client for the local DKG v10 daemon HTTP API.

    Exposes the same high-level surface as :class:`DkgHttpClient` so the CLI
    and MCP server can switch transports via ``DKG_TRANSPORT=daemon``. All
    governance (commit gate, policy evaluation, typed RDF) happens upstream;
    this class is the thin transport layer that lands the prepared payload
    on the operator's daemon.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        bearer_token: Optional[str] = None,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        self.base_url = (
            base_url or os.environ.get("DKG_BASE_URL", "http://127.0.0.1:9201")
        ).rstrip("/")
        self._bearer_token = _resolve_token(bearer_token)
        self._timeout = (
            timeout
            if timeout is not None
            else float(os.environ.get("DKG_TIMEOUT", "300"))
        )
        # Cached daemon capability: None = unprobed, True = rc.17
        # ``/api/knowledge-assets`` surface, False = pre-rc.17 legacy
        # ``/api/assertion`` routes. Set on the first WM write / share.
        self._ka_supported: Optional[bool] = None

    # -- internals -------------------------------------------------------------

    def _headers(self, json_body: bool = True) -> Dict[str, str]:
        h: Dict[str, str] = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._bearer_token}",
        }
        if json_body:
            h["Content-Type"] = "application/json"
        return h

    def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as http:
            r = http.post(f"{self.base_url}{path}", headers=self._headers(), json=body)
            r.raise_for_status()
            if not r.content:
                return {}
            return r.json()

    def _get(self, path: str) -> Dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as http:
            r = http.get(f"{self.base_url}{path}", headers=self._headers(json_body=False))
            r.raise_for_status()
            if not r.content:
                return {}
            return r.json()

    # -- payload assembly ------------------------------------------------------

    def _quads_for_artifact(
        self, request: MemoryTurnRequest, subject_uri: str
    ) -> List[Dict[str, str]]:
        """Project the typed Agience artifact onto N-Triples-style quads.

        The vocabulary mirrors the JSON-LD payload used by the MCP transport
        path so the same SPARQL queries work against either backend.
        """
        artifact_type = request.artifact_type or "Artifact"
        type_uri = f"{_AGIENCE_NS}{artifact_type}"

        quads: List[Dict[str, str]] = [
            {"subject": subject_uri, "predicate": _RDF_TYPE, "object": type_uri},
            {
                "subject": subject_uri,
                "predicate": f"{_SCHEMA_NS}name",
                "object": _lit(request.title or request.context_graph_id),
            },
            {
                "subject": subject_uri,
                "predicate": f"{_SCHEMA_NS}text",
                "object": _lit(request.markdown),
            },
            {
                "subject": subject_uri,
                "predicate": f"{_AGIENCE_NS}contextGraphId",
                "object": _lit(request.context_graph_id),
            },
            {
                "subject": subject_uri,
                "predicate": f"{_AGIENCE_NS}memoryLayer",
                "object": _lit(request.layer),
            },
        ]
        if request.artifact_id:
            quads.append({
                "subject": subject_uri,
                "predicate": f"{_AGIENCE_NS}artifactId",
                "object": _lit(request.artifact_id),
            })
        if request.author:
            quads.append({
                "subject": subject_uri,
                "predicate": f"{_AGIENCE_NS}author",
                "object": _lit(request.author),
            })
        if request.tags:
            for tag in request.tags:
                quads.append({
                    "subject": subject_uri,
                    "predicate": f"{_AGIENCE_NS}tags",
                    "object": _lit(tag),
                })
        if request.collection_id:
            quads.append({
                "subject": subject_uri,
                "predicate": f"{_AGIENCE_NS}collection",
                "object": _lit(request.collection_id),
            })
        if request.session_uri:
            quads.append({
                "subject": subject_uri,
                "predicate": f"{_SCHEMA_NS}isPartOf",
                "object": _lit(request.session_uri),
            })
        if request.sub_graph_name:
            quads.append({
                "subject": subject_uri,
                "predicate": f"{_AGIENCE_NS}subGraphName",
                "object": _lit(request.sub_graph_name),
            })
        if request.commit_receipt_id:
            quads.append({
                "subject": subject_uri,
                "predicate": f"{_AGIENCE_NS}commitReceiptId",
                "object": _lit(request.commit_receipt_id),
            })
        return quads

    # -- public API ------------------------------------------------------------

    def ping(self) -> bool:
        """Return True if ``GET /api/status`` succeeds."""
        try:
            with httpx.Client(timeout=5.0) as http:
                r = http.get(
                    f"{self.base_url}/api/status",
                    headers=self._headers(json_body=False),
                )
                return r.status_code == 200
        except Exception:
            return False

    def memory_turn(self, request: MemoryTurnRequest) -> MemoryTurnResult:
        """Project a governed Agience artifact onto the daemon.

        * ``layer == 'wm'`` → ``POST /api/knowledge-assets`` (rc.17: atomic
          create + write of an unsealed WM draft), with a one-time fallback to
          the legacy ``/api/assertion/create`` + ``/write`` on pre-rc.17 daemons.
          The result's ``turn_uri`` is the assertion URI the daemon returns.
        * ``layer == 'swm'`` → ``/api/shared-memory/write`` with
          ``localOnly: true``. The quads land on the daemon's local SWM graph
          and are eligible for an explicit ``promote`` later. ``turn_uri`` is
          the daemon-issued ``shareOperationId``.
        """
        subject_uri = (
            f"{_AGIENCE_NS}{request.context_graph_id}/"
            f"{request.artifact_id or 'unknown'}"
        )
        quads = self._quads_for_artifact(request, subject_uri)

        if request.layer == "swm":
            try:
                resp = self._post(
                    "/api/shared-memory/write",
                    {
                        "contextGraphId": request.context_graph_id,
                        "quads": quads,
                        "localOnly": True,
                    },
                )
            except httpx.HTTPStatusError as exc:
                return MemoryTurnResult(
                    turn_uri=None,
                    layer=request.layer,
                    context_graph_id=request.context_graph_id,
                    status="pending",
                    error=f"shared-memory write failed: {exc.response.status_code}",
                    raw_response={"error": str(exc)},
                )
            share_op = resp.get("shareOperationId")
            return MemoryTurnResult(
                turn_uri=share_op or None,
                layer="swm",
                context_graph_id=request.context_graph_id,
                status="anchored" if share_op else "pending",
                error=None if share_op else "no shareOperationId in response",
                raw_response=resp,
            )

        # Working Memory path. Prefer the rc.17 ``/api/knowledge-assets``
        # surface; fall back once to the legacy ``/api/assertion/*`` routes for
        # pre-rc.17 daemons (the decision is cached on ``self._ka_supported``).
        assertion_name = _safe_assertion_name(
            request.artifact_id or "",
            request.title or "",
        )
        if self._ka_supported is not False:
            result = self._wm_write_knowledge_asset(request, assertion_name, quads)
            if result is not None:
                return result
            # ``None`` ⇒ the KA route 404'd ⇒ legacy daemon; fall through.
        return self._wm_write_legacy(request, assertion_name, quads)

    def _wm_write_knowledge_asset(
        self,
        request: MemoryTurnRequest,
        assertion_name: str,
        quads: List[Dict[str, str]],
    ) -> Optional[MemoryTurnResult]:
        """rc.17 WM write via ``POST /api/knowledge-assets`` (atomic create+write).

        Sends ``finalize: false`` so the assertion stays an editable, off-chain
        WM draft (no on-chain identity) that a later ``swm/share`` can promote.
        Returns a :class:`MemoryTurnResult`, or ``None`` if the route is absent
        (HTTP 404) so the caller can fall back to the legacy assertion routes.
        """
        try:
            resp = self._post(
                "/api/knowledge-assets",
                {
                    "contextGraphId": request.context_graph_id,
                    "name": assertion_name,
                    "quads": quads,
                    "finalize": False,
                },
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                self._ka_supported = False
                return None
            return MemoryTurnResult(
                turn_uri=None,
                layer="wm",
                context_graph_id=request.context_graph_id,
                status="pending",
                error=f"knowledge-asset write failed: {exc.response.status_code}",
                raw_response={"error": (exc.response.text or "")[:500]},
            )
        self._ka_supported = True
        assertion_uri = resp.get("assertionUri") or (
            f"did:dkg:context-graph:{request.context_graph_id}/{assertion_name}"
        )
        return MemoryTurnResult(
            turn_uri=assertion_uri,
            layer="wm",
            context_graph_id=request.context_graph_id,
            status="anchored",
            error=None,
            raw_response={"knowledgeAsset": resp},
        )

    def _wm_write_legacy(
        self,
        request: MemoryTurnRequest,
        assertion_name: str,
        quads: List[Dict[str, str]],
    ) -> MemoryTurnResult:
        """Pre-rc.17 WM write via ``/api/assertion/create`` then ``/write``."""
        try:
            create_resp = self._post(
                "/api/assertion/create",
                {"contextGraphId": request.context_graph_id, "name": assertion_name},
            )
        except httpx.HTTPStatusError as exc:
            text = exc.response.text or ""
            if "already exists" not in text.lower():
                return MemoryTurnResult(
                    turn_uri=None,
                    layer="wm",
                    context_graph_id=request.context_graph_id,
                    status="pending",
                    error=f"assertion create failed: {exc.response.status_code}",
                    raw_response={"error": text[:500]},
                )
            create_resp = {"assertionUri": None, "alreadyExists": True}

        try:
            write_resp = self._post(
                f"/api/assertion/{assertion_name}/write",
                {"contextGraphId": request.context_graph_id, "quads": quads},
            )
        except httpx.HTTPStatusError as exc:
            return MemoryTurnResult(
                turn_uri=None,
                layer="wm",
                context_graph_id=request.context_graph_id,
                status="pending",
                error=f"assertion write failed: {exc.response.status_code}",
                raw_response={"error": exc.response.text[:500]},
            )

        assertion_uri = create_resp.get("assertionUri") or (
            f"did:dkg:context-graph:{request.context_graph_id}"
            f"/assertion/{assertion_name}"
        )

        return MemoryTurnResult(
            turn_uri=assertion_uri,
            layer="wm",
            context_graph_id=request.context_graph_id,
            status="anchored",
            error=None,
            raw_response={"create": create_resp, "write": write_resp},
        )

    def assertion_promote(
        self, request: AssertionPromoteRequest
    ) -> AssertionPromoteResult:
        """Curator-authorized SHARE: promote a WM assertion to Shared Memory.

        rc.17 renamed ``promote`` → ``share``: calls
        ``POST /api/knowledge-assets/{name}/swm/share``, which copies the
        assertion's quads onto the Context Graph's shared-memory view. Falls
        back once to the legacy ``POST /api/assertion/{name}/promote`` on
        pre-rc.17 daemons. On-chain Verifiable Memory is :meth:`vm_publish`.
        """
        if self._ka_supported is not False:
            try:
                resp = self._post(
                    f"/api/knowledge-assets/{request.name}/swm/share",
                    {
                        "contextGraphId": request.context_graph_id,
                        "entities": request.entities or "all",
                    },
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    self._ka_supported = False
                else:
                    return AssertionPromoteResult(
                        ok=False,
                        name=request.name,
                        raw_response={
                            "error": exc.response.text[:500],
                            "status": exc.response.status_code,
                        },
                    )
            else:
                self._ka_supported = True
                return AssertionPromoteResult(
                    ok=True, name=request.name, raw_response=resp
                )

        # Legacy fallback (pre-rc.17 daemons).
        try:
            resp = self._post(
                f"/api/assertion/{request.name}/promote",
                {
                    "contextGraphId": request.context_graph_id,
                    "entities": request.entities or "all",
                },
            )
        except httpx.HTTPStatusError as exc:
            return AssertionPromoteResult(
                ok=False,
                name=request.name,
                raw_response={
                    "error": exc.response.text[:500],
                    "status": exc.response.status_code,
                },
            )
        return AssertionPromoteResult(ok=True, name=request.name, raw_response=resp)

    def vm_publish(
        self,
        *,
        name: str,
        context_graph_id: str,
        sub_graph_name: Optional[str] = None,
        publish_epochs: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Publish a finalized + shared KA to Verifiable Memory (on-chain).

        rc.17 only: ``POST /api/knowledge-assets/{name}/vm/publish``. Mints (or
        updates) the Knowledge Asset on chain and returns the daemon's publish
        receipt (``{kaId, status, ual, txHash, merkleRoot, ...}``).

        Preconditions enforced by the daemon: the assertion must be **finalized**
        (sealed via ``wm/finalize``) and **shared** to SWM, the Context Graph
        must be on-chain registered, and the node needs gas + TRAC and a reliable
        chain RPC. Returns ``{"ok": False, "error": ...}`` on failure rather than
        raising, so callers can treat VM publish as best-effort.
        """
        body: Dict[str, Any] = {"contextGraphId": context_graph_id}
        options: Dict[str, Any] = {}
        if sub_graph_name:
            body["subGraphName"] = sub_graph_name
        if publish_epochs is not None:
            options["publishEpochs"] = publish_epochs
        if options:
            body["options"] = options
        try:
            resp = self._post(
                f"/api/knowledge-assets/{name}/vm/publish", body
            )
        except httpx.HTTPStatusError as exc:
            return {
                "ok": False,
                "status": exc.response.status_code,
                "error": (exc.response.text or "")[:500],
            }
        return {"ok": resp.get("status") == "confirmed", **resp}

    def memory_search(self, request: MemorySearchRequest) -> MemorySearchResult:
        """Search Working / Shared Memory via SPARQL ``POST /api/query``.

        Filters by ``agience:contextGraphId`` and free-text ``schema:text``;
        memory layer filtering is honoured when ``request.memory_layers`` is
        provided.
        """
        layers = request.memory_layers
        layer_filter = ""
        if layers:
            quoted = ", ".join(f'"{l}"' for l in layers)
            layer_filter = f"FILTER (?memoryLayer IN ({quoted}))"

        # Assertion writes land on named sub-graphs (one per assertion plus the
        # ``_shared_memory`` graph for SWM), so we must traverse them via
        # ``GRAPH ?g { ... }`` rather than the default graph. The daemon's
        # SPARQL parser accepts standard PREFIX declarations as long as they
        # precede SELECT on their own lines.
        sparql = f"""PREFIX schema: <{_SCHEMA_NS}>
PREFIX agience: <{_AGIENCE_NS}>
SELECT ?s ?name ?text ?memoryLayer ?artifactId ?author ?collection WHERE {{
  GRAPH ?g {{
    ?s schema:text ?text .
    OPTIONAL {{ ?s schema:name ?name . }}
    OPTIONAL {{ ?s agience:memoryLayer ?memoryLayer . }}
    OPTIONAL {{ ?s agience:artifactId ?artifactId . }}
    OPTIONAL {{ ?s agience:author ?author . }}
    OPTIONAL {{ ?s agience:collection ?collection . }}
  }}
  FILTER (CONTAINS(STR(?s), "{request.context_graph_id}") || CONTAINS(STR(?name), "{request.context_graph_id}"))
  FILTER (CONTAINS(LCASE(STR(?text)), LCASE("{request.query}")))
  {layer_filter}
}}
LIMIT {request.limit}"""

        try:
            # NOTE: do NOT pass ``contextGraphId`` in the body. On rc.17 the
            # daemon uses it to scope ``/api/query`` to a meta-only view that
            # excludes the real ``…/_shared_memory/…`` and ``…/_working_memory/…``
            # content graphs, so a scoped query never sees the promoted quads.
            # Scope is enforced inside the SPARQL via ``CONTAINS(STR(?s), cgId)``.
            resp = self._post("/api/query", {"sparql": sparql})
        except httpx.HTTPStatusError as exc:
            return MemorySearchResult(
                result_count=0,
                results=[],
                raw_response={
                    "error": exc.response.text[:500],
                    "status": exc.response.status_code,
                },
            )

        result = resp.get("result", {})
        bindings = result.get("bindings", []) if isinstance(result, dict) else []

        rows: List[Dict[str, Any]] = []
        for binding in bindings:
            if isinstance(binding, dict):
                row = {k: v.get("value") if isinstance(v, dict) else v for k, v in binding.items()}
                rows.append(row)

        return MemorySearchResult(
            result_count=len(rows),
            results=rows,
            raw_response=resp,
        )
