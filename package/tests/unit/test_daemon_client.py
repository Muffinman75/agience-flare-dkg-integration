"""Unit tests for DkgDaemonClient.

The daemon transport speaks plain JSON over HTTP, so these tests stub the
client's ``_post``/``_get`` methods to verify request shape, payload mapping,
and error handling without contacting a live daemon. End-to-end behaviour
against a real daemon is covered by the integration test suite.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

import httpx
import pytest

from agience_dkg_integration.daemon_client import (
    DkgDaemonClient,
    _lit,
    _resolve_token,
    _safe_assertion_name,
)
from agience_dkg_integration.models import (
    AssertionPromoteRequest,
    MemorySearchRequest,
    MemoryTurnRequest,
)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


class _StubDaemonClient(DkgDaemonClient):
    """DkgDaemonClient with _post/_get replaced by recorded canned responses."""

    def __init__(self, post_responses: Dict[str, Dict[str, Any]] | None = None,
                 post_errors: Dict[str, int] | None = None) -> None:
        super().__init__(base_url="http://127.0.0.1:9201", bearer_token="unit-test-token")
        self._post_responses = post_responses or {}
        self._post_errors = post_errors or {}
        self.posts: List[Tuple[str, Dict[str, Any]]] = []

    def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        self.posts.append((path, body))
        if path in self._post_errors:
            status = self._post_errors[path]
            request = httpx.Request("POST", f"{self.base_url}{path}")
            response = httpx.Response(status, json={"error": "stubbed failure"}, request=request)
            raise httpx.HTTPStatusError("stubbed", request=request, response=response)
        return self._post_responses.get(path, {})


# ----------------------------------------------------------------------------
# Pure helpers
# ----------------------------------------------------------------------------


def test_lit_escapes_quotes_and_newlines() -> None:
    assert _lit('plain') == '"plain"'
    assert _lit('he said "hi"') == '"he said \\"hi\\""'
    assert _lit('line1\nline2') == '"line1\\nline2"'
    assert _lit('back\\slash') == '"back\\\\slash"'


def test_safe_assertion_name_strips_unsafe_chars() -> None:
    assert _safe_assertion_name("adr-001", "My Decision!") == "adr-001-My-Decision"
    assert _safe_assertion_name("", "") == "agience-artifact"
    # Underscores are allowed in the safe set
    assert _safe_assertion_name("a_b") == "a_b"


def test_resolve_token_explicit_wins(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DKG_DAEMON_TOKEN", "env-daemon")
    monkeypatch.setenv("DKG_TOKEN", "env-mcp")
    assert _resolve_token("explicit-tok") == "explicit-tok"


def test_resolve_token_prefers_daemon_env_over_auth_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DKG_DAEMON_TOKEN", "env-daemon")
    monkeypatch.delenv("DKG_TOKEN", raising=False)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    auth_dir = tmp_path / ".dkg"
    auth_dir.mkdir()
    (auth_dir / "auth.token").write_text("# header\nfile-token\n")
    assert _resolve_token(None) == "env-daemon"


def test_resolve_token_prefers_auth_file_over_dkg_token(tmp_path, monkeypatch) -> None:
    """The daemon should never trust a DKG_TOKEN that may be MCP-flavoured."""
    monkeypatch.delenv("DKG_DAEMON_TOKEN", raising=False)
    monkeypatch.setenv("DKG_TOKEN", "mcp-flavour")
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    auth_dir = tmp_path / ".dkg"
    auth_dir.mkdir()
    (auth_dir / "auth.token").write_text("# DKG node token\nfile-token\n")
    assert _resolve_token(None) == "file-token"


def test_resolve_token_falls_back_to_dkg_token(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DKG_DAEMON_TOKEN", raising=False)
    monkeypatch.setenv("DKG_TOKEN", "fallback")
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    # No auth.token file
    assert _resolve_token(None) == "fallback"


# ----------------------------------------------------------------------------
# memory_turn — Working Memory path
# ----------------------------------------------------------------------------


def test_memory_turn_wm_creates_knowledge_asset_and_writes_quads() -> None:
    ka_resp = {
        "name": "adr-1-Title",
        "assertionUri": "did:dkg:context-graph:cg-1/adr-1-Title",
        "alreadyExists": False,
        "status": "draft-open",
        "written": 8,
    }
    client = _StubDaemonClient(post_responses={"/api/knowledge-assets": ka_resp})

    request = MemoryTurnRequest(
        contextGraphId="cg-1",
        markdown="**Title:** T\n\nBody",
        artifactType="Decision",
        artifactId="adr-1",
        title="Title",
        author="alice",
    )
    result = client.memory_turn(request)

    assert result.layer == "wm"
    assert result.status == "anchored"
    assert result.error is None
    assert result.turn_uri == ka_resp["assertionUri"]
    assert client._ka_supported is True

    # A single atomic create+write call to the v10.0.1 KA surface.
    assert len(client.posts) == 1
    create_call = client.posts[0]
    assert create_call[0] == "/api/knowledge-assets"
    assert create_call[1]["contextGraphId"] == "cg-1"
    assert create_call[1]["name"] == "adr-1-Title"
    # WM-only draft: never seal on a plain wm-write.
    assert create_call[1]["finalize"] is False
    quads = create_call[1]["quads"]
    assert any(q["predicate"].endswith("memoryLayer") for q in quads)
    assert any(q["object"] == '"alice"' for q in quads)


def test_memory_turn_wm_handles_already_exists() -> None:
    """v10.0.1 surfaces re-runs natively via alreadyExists; still anchored."""
    ka_resp = {
        "name": "already-exists",
        "assertionUri": "did:dkg:context-graph:cg-1/already-exists",
        "alreadyExists": True,
        "status": "draft-open",
        "written": 5,
    }
    client = _StubDaemonClient(post_responses={"/api/knowledge-assets": ka_resp})

    result = client.memory_turn(MemoryTurnRequest(
        contextGraphId="cg-1",
        markdown="body",
        artifactId="already",
        title="exists",
    ))
    assert result.status == "anchored"
    assert "already-exists" in (result.turn_uri or "")


def test_memory_turn_wm_returns_pending_on_ka_failure() -> None:
    client = _StubDaemonClient(post_errors={"/api/knowledge-assets": 500})

    result = client.memory_turn(MemoryTurnRequest(
        contextGraphId="cg-1",
        markdown="body",
        artifactId="x",
        title="y",
    ))
    assert result.status == "pending"
    assert result.error is not None
    assert "500" in result.error


def test_memory_turn_wm_falls_back_to_legacy_on_404() -> None:
    """A pre-v10.0.1 daemon (no KA route) falls back to /api/assertion/*."""
    create_resp = {
        "assertionUri": "did:dkg:context-graph:cg-1/assertion/0xWALLET/adr-1-Title",
    }

    def _post(path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        client.posts.append((path, body))
        if path == "/api/knowledge-assets":
            request = httpx.Request("POST", f"{client.base_url}{path}")
            response = httpx.Response(404, text="not found", request=request)
            raise httpx.HTTPStatusError("nf", request=request, response=response)
        if path == "/api/assertion/create":
            return create_resp
        return {"written": 8}

    client = _StubDaemonClient()
    client._post = _post  # type: ignore[assignment]

    result = client.memory_turn(MemoryTurnRequest(
        contextGraphId="cg-1",
        markdown="body",
        artifactId="adr-1",
        title="Title",
    ))
    assert result.status == "anchored"
    assert client._ka_supported is False
    paths = [p for p, _ in client.posts]
    assert paths[0] == "/api/knowledge-assets"
    assert "/api/assertion/create" in paths
    assert any(p.endswith("/write") for p in paths)


# ----------------------------------------------------------------------------
# memory_turn — Shared Memory path
# ----------------------------------------------------------------------------


def test_memory_turn_swm_writes_localonly() -> None:
    swm_resp = {
        "shareOperationId": "swm-1779480199605-test",
        "contextGraphId": "cg-1",
        "graph": "did:dkg:context-graph:cg-1/_shared_memory",
        "triplesWritten": 6,
    }
    client = _StubDaemonClient(post_responses={"/api/shared-memory/write": swm_resp})

    result = client.memory_turn(MemoryTurnRequest(
        contextGraphId="cg-1",
        layer="swm",
        markdown="body",
        artifactId="swm-1",
        title="t",
    ))
    assert result.status == "anchored"
    assert result.layer == "swm"
    assert result.turn_uri == "swm-1779480199605-test"

    call = client.posts[0]
    assert call[0] == "/api/shared-memory/write"
    assert call[1]["localOnly"] is True
    assert call[1]["contextGraphId"] == "cg-1"


def test_memory_turn_swm_pending_on_failure() -> None:
    client = _StubDaemonClient(post_errors={"/api/shared-memory/write": 503})
    result = client.memory_turn(MemoryTurnRequest(
        contextGraphId="cg-1", layer="swm", markdown="b", artifactId="x", title="y",
    ))
    assert result.status == "pending"
    assert result.error and "503" in result.error


# ----------------------------------------------------------------------------
# assertion_promote
# ----------------------------------------------------------------------------


def test_assertion_promote_calls_share_endpoint() -> None:
    client = _StubDaemonClient(post_responses={
        "/api/knowledge-assets/abc-123/swm/share": {"swmShared": True, "promotedCount": 4},
    })
    result = client.assertion_promote(AssertionPromoteRequest(name="abc-123", contextGraphId="cg-1"))
    assert result.ok is True
    assert result.name == "abc-123"
    assert client.posts[0][0] == "/api/knowledge-assets/abc-123/swm/share"
    assert client._ka_supported is True


def test_assertion_promote_marks_failure() -> None:
    client = _StubDaemonClient(post_errors={"/api/knowledge-assets/abc-123/swm/share": 500})
    result = client.assertion_promote(AssertionPromoteRequest(name="abc-123", contextGraphId="cg-1"))
    assert result.ok is False


def test_assertion_promote_falls_back_to_legacy_on_404() -> None:
    def _post(path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        client.posts.append((path, body))
        if path.endswith("/swm/share"):
            request = httpx.Request("POST", f"{client.base_url}{path}")
            response = httpx.Response(404, text="nf", request=request)
            raise httpx.HTTPStatusError("nf", request=request, response=response)
        return {"ok": True}

    client = _StubDaemonClient()
    client._post = _post  # type: ignore[assignment]

    result = client.assertion_promote(AssertionPromoteRequest(name="abc-123", contextGraphId="cg-1"))
    assert result.ok is True
    assert client._ka_supported is False
    paths = [p for p, _ in client.posts]
    assert paths[0] == "/api/knowledge-assets/abc-123/swm/share"
    assert paths[1] == "/api/assertion/abc-123/promote"


# ----------------------------------------------------------------------------
# vm_publish (Verifiable Memory — v10.0.1)
# ----------------------------------------------------------------------------


def test_vm_publish_confirmed() -> None:
    client = _StubDaemonClient(post_responses={
        "/api/knowledge-assets/abc-123/vm/publish": {
            "kaId": "42", "status": "confirmed",
            "ual": "did:dkg:base:84532/0xKA/42", "txHash": "0xabc",
        },
    })
    result = client.vm_publish(name="abc-123", context_graph_id="cg-1")
    assert result["ok"] is True
    assert result["ual"].endswith("/42")
    assert client.posts[0][0] == "/api/knowledge-assets/abc-123/vm/publish"
    assert client.posts[0][1]["contextGraphId"] == "cg-1"


def test_vm_publish_reports_failure() -> None:
    client = _StubDaemonClient(post_errors={"/api/knowledge-assets/abc-123/vm/publish": 502})
    result = client.vm_publish(name="abc-123", context_graph_id="cg-1")
    assert result["ok"] is False
    assert result["status"] == 502


# ----------------------------------------------------------------------------
# memory_search
# ----------------------------------------------------------------------------


def test_memory_search_sends_graph_scoped_sparql() -> None:
    bindings_resp = {
        "result": {
            "bindings": [
                {
                    "s": {"value": "https://agience.ai/ontology/cg-1/adr-1"},
                    "name": {"value": '"ADR title"'},
                    "text": {"value": '"body"'},
                }
            ]
        }
    }
    client = _StubDaemonClient(post_responses={"/api/query": bindings_resp})

    result = client.memory_search(MemorySearchRequest(
        contextGraphId="cg-1",
        query="adr",
        limit=5,
        memoryLayers=["wm"],
    ))

    assert result.result_count == 1
    assert result.results[0]["s"] == "https://agience.ai/ontology/cg-1/adr-1"

    call = client.posts[0]
    assert call[0] == "/api/query"
    sparql = call[1]["sparql"]
    assert "GRAPH ?g" in sparql, "Search must traverse named sub-graphs"
    assert "schema:text" in sparql
    assert "agience:memoryLayer" in sparql
    assert 'IN ("wm")' in sparql
    # Regression: must NOT pass contextGraphId in the body. v10.0.1 uses it to
    # scope /api/query to a meta-only view that excludes the real
    # …/_shared_memory/… content graphs, so a scoped query never sees the
    # shared quads. Scope is enforced inside the SPARQL instead.
    assert "contextGraphId" not in call[1]
    assert 'CONTAINS(STR(?s), "cg-1")' in sparql


def test_memory_search_returns_empty_on_failure() -> None:
    client = _StubDaemonClient(post_errors={"/api/query": 500})
    result = client.memory_search(MemorySearchRequest(
        contextGraphId="cg-1", query="x", limit=1, memoryLayers=None,
    ))
    assert result.result_count == 0
    assert result.results == []
