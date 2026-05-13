"""MCP stdio server exposing Agience DKG Working Memory tools.

Run as:
    agience-dkg-mcp          (installed entry-point)
    python -m agience_dkg_integration.mcp_server   (module mode)

Environment variables:
    DKG_BASE_URL   – DKG v10 node URL (default http://localhost:8081)
    DKG_TOKEN      – Bearer token for the DKG node
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Sequence

from ._env import load_env

load_env()

from .agience_client import (
    AgienceClient,
    AgienceClientError,
    ArtifactNotCommittedError,
)
from .client import DkgHttpClient
from .formatter import artifact_to_markdown, session_uri_for_collection
from .models import AssertionPromoteRequest, MemorySearchRequest, MemoryTurnRequest


def _read_message() -> Dict[str, Any] | None:
    """Read a JSON-RPC message from stdin (Content-Length framed)."""
    header = ""
    while True:
        line = sys.stdin.readline()
        if not line:
            return None
        header += line
        if line.strip() == "":
            break

    content_length = 0
    for h in header.strip().splitlines():
        if h.lower().startswith("content-length:"):
            content_length = int(h.split(":", 1)[1].strip())

    if content_length == 0:
        return None

    body = sys.stdin.read(content_length)
    return json.loads(body)


def _write_message(msg: Dict[str, Any]) -> None:
    """Write a JSON-RPC message to stdout (Content-Length framed)."""
    body = json.dumps(msg)
    encoded = body.encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("utf-8"))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "agience_wm_write",
        "description": (
            "Write a governed Agience artifact to DKG v10 Working Memory as a typed "
            "`agience:` Knowledge Asset. Unlike raw `dkg-create` (which accepts free-form "
            "payloads from any agent), this records artifact metadata (type, author, "
            "collection, sessionUri, memoryLayer) with the `agience:` RDF vocabulary so "
            "the resulting asset is SPARQL-queryable by type across Context Graphs and "
            "preserves the provenance chain back to the originating Agience commit. "
            "Returns the UAL (turn_uri) and an explicit anchored/pending status that "
            "distinguishes MCP transport success from blockchain anchoring state."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "from_agience_artifact": {
                    "type": "string",
                    "description": (
                        "GOVERNED MODE: fetch the named artifact from a running "
                        "Agience instance (AGIENCE_BASE_URL / AGIENCE_TOKEN) and "
                        "refuse to project unless its state is 'committed'. When set, "
                        "title/artifact_type/artifact_id/content/etc. become optional "
                        "overrides; values come from the Agience record."
                    ),
                },
                "title": {"type": "string", "description": "Artifact title (required unless from_agience_artifact is set)"},
                "artifact_type": {
                    "type": "string",
                    "description": "Artifact type: architecture-decision, research-note, claim, citation, summary",
                },
                "artifact_id": {"type": "string", "description": "Stable artifact identifier"},
                "content": {"type": "string", "description": "Artifact body text"},
                "context_graph_id": {"type": "string", "description": "DKG Context Graph ID"},
                "collection_id": {"type": "string", "description": "Agience collection ID (groups assets under a sessionUri)"},
                "author": {"type": "string", "description": "Author display name"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for the artifact",
                },
            },
            "required": ["context_graph_id"],
        },
    },
    {
        "name": "agience_promote",
        "description": (
            "Promote a Working Memory Knowledge Asset to Shared Memory (the v10 SHARE "
            "operation). Curator-authorized and explicit — never automatic and never "
            "triggered as a side effect of a write. Eligibility is gated upstream by the "
            "Agience `PolicyMappingRecord.promotion_profile` (must be `swm-eligible` or "
            "`vm-eligible`). Publishes as a public Knowledge Asset via `dkg-create` "
            "(privacy=public) while preserving the UAL chain for Round 2 Verified Memory."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "turn_uri": {
                    "type": "string",
                    "description": "UAL / turn_uri returned by agience_wm_write",
                },
                "context_graph_id": {"type": "string", "description": "DKG Context Graph ID"},
            },
            "required": ["turn_uri", "context_graph_id"],
        },
    },
    {
        "name": "agience_search",
        "description": (
            "Search Working Memory and/or Shared Memory for typed Agience Knowledge Assets "
            "via SPARQL using the `agience:` RDF vocabulary. Filterable by memory layer, "
            "artifact type, author, collection, and sessionUri — not opaque blob retrieval. "
            "Read-only. Returns matching Knowledge Assets scoped to the specified "
            "Context Graph."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "context_graph_id": {"type": "string", "description": "DKG Context Graph ID"},
                "limit": {"type": "integer", "description": "Maximum results (default 20)"},
                "memory_layers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by memory layers: wm, swm (default: all)",
                },
            },
            "required": ["query", "context_graph_id"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

def _get_client() -> DkgHttpClient:
    base_url = os.environ.get("DKG_BASE_URL", "http://localhost:8081")
    token = os.environ.get("DKG_TOKEN", "")
    if not token:
        raise RuntimeError("DKG_TOKEN environment variable is required")
    return DkgHttpClient(base_url=base_url, bearer_token=token)


def _execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Execute a tool and return a text result."""
    client = _get_client()

    if name == "agience_wm_write":
        from_artifact_id = arguments.get("from_agience_artifact", "")
        title = arguments.get("title", "")
        artifact_type = arguments.get("artifact_type", "")
        artifact_id = arguments.get("artifact_id", "")
        content = arguments.get("content", "")
        author = arguments.get("author")
        tags = arguments.get("tags", []) or []
        collection_id = arguments.get("collection_id", "")
        commit_receipt_id: str | None = None

        if from_artifact_id:
            ag = AgienceClient()
            artifact = ag.get_committed_artifact(from_artifact_id)
            title = title or artifact.title
            artifact_type = artifact_type or artifact.artifact_type
            artifact_id = artifact_id or artifact.id
            content = content or artifact.content
            author = author or artifact.author
            if not tags and artifact.tags:
                tags = artifact.tags
            collection_id = collection_id or (artifact.collection_id or "")
            commit_receipt_id = artifact.commit_receipt_id

        missing = [
            n
            for n, v in (
                ("title", title),
                ("artifact_type", artifact_type),
                ("artifact_id", artifact_id),
                ("content", content),
            )
            if not v
        ]
        if missing:
            raise ValueError(
                f"Missing required field(s): {', '.join(missing)}. "
                "Supply them directly or use from_agience_artifact."
            )

        markdown = artifact_to_markdown(
            title=title,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            content=content,
            author=author,
            tags=tags,
            collection_id=collection_id or None,
        )
        session_uri = session_uri_for_collection(collection_id) if collection_id else None
        request = MemoryTurnRequest(
            contextGraphId=arguments["context_graph_id"],
            markdown=markdown,
            layer="wm",
            sessionUri=session_uri,
            artifactType=artifact_type,
            artifactId=artifact_id,
            title=title,
            author=author,
            tags=tags or None,
            collectionId=collection_id or None,
            commitReceiptId=commit_receipt_id,
        )
        result = client.memory_turn(request)
        return result.model_dump_json(indent=2)

    elif name == "agience_promote":
        turn_uri = arguments["turn_uri"]
        ref = turn_uri.split("/")[-1]
        request = AssertionPromoteRequest(
            name=ref,
            contextGraphId=arguments["context_graph_id"],
        )
        result = client.assertion_promote(request)
        return result.model_dump_json(indent=2)

    elif name == "agience_search":
        request = MemorySearchRequest(
            contextGraphId=arguments["context_graph_id"],
            query=arguments["query"],
            limit=arguments.get("limit", 20),
            memoryLayers=arguments.get("memory_layers"),
        )
        result = client.memory_search(request)
        return result.model_dump_json(indent=2)

    else:
        raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# JSON-RPC message loop
# ---------------------------------------------------------------------------

def _handle_message(msg: Dict[str, Any]) -> Dict[str, Any] | None:
    """Handle a single JSON-RPC request and return a response (or None for notifications)."""
    method = msg.get("method", "")
    msg_id = msg.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "agience-dkg",
                    "version": "0.2.0",
                },
            },
        }

    elif method == "notifications/initialized":
        return None

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": TOOLS},
        }

    elif method == "tools/call":
        params = msg.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            text = _execute_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": text}],
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {exc}"}],
                    "isError": True,
                },
            }

    else:
        if msg_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        return None


def main() -> None:
    """Run the MCP stdio server."""
    sys.stderr.write("agience-dkg MCP server running on stdio\n")
    sys.stderr.flush()

    while True:
        msg = _read_message()
        if msg is None:
            break
        response = _handle_message(msg)
        if response is not None:
            _write_message(response)


if __name__ == "__main__":
    main()
