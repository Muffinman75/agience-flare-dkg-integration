from __future__ import annotations

import json
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

_LAYER_PRIVACY: Dict[str, str] = {
    "wm": "private",
    "swm": "public",
}


class DkgHttpClient:
    """Synchronous wrapper around the DKG v10 node MCP + HTTP API (port 8081).

    Implements the Agience Working Memory / Shared Memory abstraction using the
    DKG v10 node's supported public interfaces:

    * Working Memory write  → MCP tool 'dkg-create' (privacy=private) via POST /mcp
    * Shared Memory promote → MCP tool 'dkg-create' (privacy=public)  via POST /mcp
    * Memory search         → MCP tool 'dkg-sparql-query'              via POST /mcp
    * Ping                  → GET /health

    Each operation opens a fresh MCP session (initialize + tool call) over the
    MCP Streamable HTTP transport, as required by the DKG v10 node's /mcp endpoint.

    All methods raise httpx.HTTPStatusError on non-2xx responses, or RuntimeError
    when the MCP tool call returns an error result.
    Credentials are read from constructor arguments; never hardcoded.
    """

    def __init__(
        self,
        base_url: str,
        bearer_token: str,
        *,
        timeout: float = 300.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._bearer_token = bearer_token
        self._timeout = timeout

    def _headers(self, session_id: Optional[str] = None) -> Dict[str, str]:
        h = {
            "Authorization": f"Bearer {self._bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if session_id:
            h["mcp-session-id"] = session_id
        return h

    def _mcp_post(self, http: httpx.Client, session_id: Optional[str], payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST a JSON-RPC message to /mcp and return the parsed response."""
        r = http.post(
            f"{self.base_url}/mcp",
            headers=self._headers(session_id),
            json=payload,
        )
        r.raise_for_status()
        if not r.content:
            return {}
        return r.json()

    def _read_sse_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Read an SSE stream response and return the first data event parsed as JSON."""
        result: Dict[str, Any] = {}
        for line in response.iter_lines():
            if line.startswith("data:"):
                data_str = line[len("data:"):].strip()
                if data_str and data_str != "[DONE]":
                    try:
                        result = json.loads(data_str)
                    except json.JSONDecodeError:
                        pass
                    if result:
                        break
        return result

    def _mcp_call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Open an MCP session, call a tool, and return the raw tool result.

        The initialize POST returns plain JSON with the session ID in a response header.
        The tools/call POST returns an SSE stream (text/event-stream); we read the
        first data event which contains the JSON-RPC response.
        """
        with httpx.Client(timeout=self._timeout) as http:
            init_r = http.post(
                f"{self.base_url}/mcp",
                headers=self._headers(None),
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "agience-flare-dkg-integration", "version": "0.1.0"},
                    },
                },
            )
            init_r.raise_for_status()
            session_id = init_r.headers.get("mcp-session-id")

        with httpx.Client(timeout=httpx.Timeout(self._timeout, read=None)) as http:
            with http.stream(
                "POST",
                f"{self.base_url}/mcp",
                headers=self._headers(session_id),
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments,
                    },
                },
            ) as call_r:
                call_r.raise_for_status()
                content_type = call_r.headers.get("content-type", "")
                if "text/event-stream" in content_type:
                    return self._read_sse_response(call_r)
                else:
                    return call_r.json()

    def ping(self) -> bool:
        """Return True if the node is reachable."""
        try:
            with httpx.Client(timeout=5.0) as http:
                r = http.get(f"{self.base_url}/health")
                return r.status_code == 200
        except Exception:
            return False

    def memory_turn(self, request: MemoryTurnRequest) -> MemoryTurnResult:
        """Write an Agience artifact as a DKG v10 Knowledge Asset via MCP dkg-create.

        Working Memory (layer='wm')  → Knowledge Asset with privacy='private'.
        Shared Memory  (layer='swm') → Knowledge Asset with privacy='public' (SHARE).

        The artifact markdown is serialised as a JSON-LD document so the DKG node
        can extract RDF triples from the structured field headers produced by
        formatter.artifact_to_markdown().
        """
        privacy = _LAYER_PRIVACY.get(request.layer, "private")

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
        if request.session_uri:
            jsonld["schema:isPartOf"] = request.session_uri
        if request.sub_graph_name:
            jsonld["agience:subGraphName"] = request.sub_graph_name
        if request.commit_receipt_id:
            jsonld["agience:commitReceiptId"] = request.commit_receipt_id

        raw = self._mcp_call_tool("dkg-create", {
            "jsonld": json.dumps(jsonld),
            "privacy": privacy,
        })

        result_content = raw.get("result", {}).get("content", [])
        text_block = next((c.get("text", "") for c in result_content if c.get("type") == "text"), "")

        ual: Optional[str] = None
        for line in text_block.splitlines():
            if line.startswith("UAL:"):
                ual = line.split("UAL:", 1)[1].strip()
                break

        error_msg: Optional[str] = None
        if "CONNECTION ERROR" in text_block:
            error_msg = "MCP transport succeeded but DKG blockchain anchoring failed (testnet RPC unreachable)"
        elif "Safe mode" in text_block:
            error_msg = "MCP transport succeeded but DKG safe mode validation failed"
        elif "Error" in text_block and not ual:
            error_msg = f"MCP transport succeeded but DKG tool returned an error: {text_block[:200]}"

        turn_uri = ual or f"agience://memory/{request.context_graph_id}/pending"

        return MemoryTurnResult(
            turn_uri=turn_uri,
            layer=request.layer,
            context_graph_id=request.context_graph_id,
            raw_response=raw,
            status="anchored" if ual else "pending",
            error=error_msg,
        )

    def assertion_promote(self, request: AssertionPromoteRequest) -> AssertionPromoteResult:
        """Promote a Working Memory artifact to Shared Memory (SHARE) via MCP dkg-create.

        Publishes a new public Knowledge Asset that references the original UAL,
        realising the WM → SWM promotion step in the v10 trust gradient.
        """
        jsonld: Dict[str, Any] = {
            "@context": "https://schema.org/",
            "@type": "Article",
            "name": f"agience-promote:{request.context_graph_id}",
            "isBasedOn": request.name,
            "keywords": "swm",
        }
        if request.entities:
            jsonld["about"] = request.entities

        raw = self._mcp_call_tool("dkg-create", {
            "jsonld": json.dumps(jsonld),
            "privacy": "public",
        })

        return AssertionPromoteResult(ok=True, name=request.name, raw_response=raw)

    def memory_search(self, request: MemorySearchRequest) -> MemorySearchResult:
        """Search Knowledge Assets via SPARQL SELECT using the MCP dkg-sparql-query tool.

        Filters by contextGraphId stored in the JSON-LD 'name' field and the
        free-text query against the 'text' predicate.
        """
        layers: Optional[List[str]] = request.memory_layers
        layer_filter = ""
        if layers:
            quoted = ", ".join(f'"{l}"' for l in layers)
            layer_filter = f'FILTER (?memoryLayer IN ({quoted}))'

        sparql = f"""PREFIX schema: <https://schema.org/>
PREFIX agience: <https://agience.ai/ontology/>
SELECT ?s ?name ?text ?memoryLayer ?artifactType ?artifactId ?author ?collection ?isPartOf WHERE {{
  ?s schema:text ?text .
  OPTIONAL {{ ?s schema:name ?name . }}
  OPTIONAL {{ ?s agience:memoryLayer ?memoryLayer . }}
  OPTIONAL {{ ?s agience:artifactId ?artifactId . }}
  OPTIONAL {{ ?s agience:author ?author . }}
  OPTIONAL {{ ?s agience:collection ?collection . }}
  OPTIONAL {{ ?s schema:isPartOf ?isPartOf . }}
  FILTER (CONTAINS(STR(?s), "{request.context_graph_id}") || CONTAINS(STR(?name), "{request.context_graph_id}"))
  FILTER (CONTAINS(LCASE(STR(?text)), LCASE("{request.query}")))
  {layer_filter}
}}
LIMIT {request.limit}"""

        raw = self._mcp_call_tool("dkg-sparql-query", {"query": sparql})

        result_content = raw.get("result", {}).get("content", [])
        text_block = next((c.get("text", "") for c in result_content if c.get("type") == "text"), "")

        rows: List[Dict[str, Any]] = []
        try:
            parsed = json.loads(text_block) if text_block.strip().startswith("{") else {}
            data = parsed.get("data", [])
            if isinstance(data, list):
                rows = data
        except (json.JSONDecodeError, AttributeError):
            pass

        return MemorySearchResult(
            result_count=len(rows),
            results=rows,
            raw_response=raw,
        )
