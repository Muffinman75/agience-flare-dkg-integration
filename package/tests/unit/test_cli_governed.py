"""Tests for the CLI's governed-mode (`--from-agience-artifact`).

These tests prove that the integration enforces the human-review commit
boundary in code: only artifacts with state == 'committed' can be projected
to DKG.
"""

from __future__ import annotations

from typing import Any, Dict

import httpx
import pytest
from typer.testing import CliRunner

import agience_dkg_integration.agience_client as agience_client_mod
import agience_dkg_integration.client as dkg_client_mod
import agience_dkg_integration.daemon_client as dkg_daemon_mod
from agience_dkg_integration.cli import app

runner = CliRunner()


def _patch_agience(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    original = httpx.Client

    def _factory(*args, **kwargs):
        kwargs.pop("transport", None)
        return original(*args, transport=transport, **kwargs)

    monkeypatch.setattr(agience_client_mod.httpx, "Client", _factory)


def _patch_dkg_memory_turn(monkeypatch, captured: Dict[str, Any]):
    """Replace `memory_turn` on **both** DKG transports with a recorder.

    The CLI's default transport is `daemon` (DkgDaemonClient); MCP remains a
    fully-supported alternative. These tests assert governance-flow behaviour
    that is transport-independent, so we patch both clients to keep the
    suite stable regardless of which transport the CLI happens to pick.
    """
    from agience_dkg_integration.models import MemoryTurnResult

    def fake_memory_turn(self, request):
        captured["request"] = request
        return MemoryTurnResult(
            turnUri="agience://memory/cg-1/abc",
            layer=request.layer,
            contextGraphId=request.context_graph_id,
            status="anchored",
            error=None,
            raw_response={"mock": True},
        )

    monkeypatch.setattr(dkg_client_mod.DkgHttpClient, "memory_turn", fake_memory_turn)
    monkeypatch.setattr(dkg_daemon_mod.DkgDaemonClient, "memory_turn", fake_memory_turn)


def test_governed_mode_projects_committed_artifact(monkeypatch):
    """Happy path: a committed Agience artifact is fetched and projected.

    Verifies:
    - Title/type/content/etc. flow through from Agience into the DKG request
    - commit_receipt_id is attached
    """

    publications: list[Dict[str, Any]] = []

    def agience_handler(request: httpx.Request) -> httpx.Response:
        # Best-effort provenance write-back after a successful WM write.
        if request.method == "POST" and request.url.path.endswith("/dkg/publication"):
            assert request.url.path == "/artifacts/art-001/dkg/publication"
            import json as _json

            publications.append(_json.loads(request.content))
            return httpx.Response(200, json={"ok": True})
        assert request.url.path == "/artifacts/art-001"
        return httpx.Response(
            200,
            json={
                "id": "art-001",
                "state": "committed",
                "title": "Architecture Decision: DKG v10",
                "type": "architecture-decision",
                "content": "We will use DKG v10 Working Memory.",
                "author": "Manoj",
                "tags": ["architecture", "dkg-v10"],
                "collection_id": "agience-architecture",
                "commit_receipt_id": "rcpt-abc-123",
            },
        )

    captured: Dict[str, Any] = {}
    _patch_agience(monkeypatch, agience_handler)
    _patch_dkg_memory_turn(monkeypatch, captured)
    monkeypatch.setenv("DKG_TOKEN", "dkg-tok")
    monkeypatch.setenv("AGIENCE_BASE_URL", "http://agience.test")
    monkeypatch.setenv("AGIENCE_TOKEN", "ag-tok")

    result = runner.invoke(
        app,
        [
            "wm-write",
            "--context-graph-id", "cg-1",
            "--from-agience-artifact", "art-001",
        ],
    )

    assert result.exit_code == 0, result.output
    req = captured["request"]
    assert req.title == "Architecture Decision: DKG v10"
    assert req.artifact_type == "architecture-decision"
    assert req.artifact_id == "art-001"
    assert req.author == "Manoj"
    assert req.tags == ["architecture", "dkg-v10"]
    assert req.collection_id == "agience-architecture"
    assert req.commit_receipt_id == "rcpt-abc-123"
    assert "We will use DKG v10" in req.markdown

    # The best-effort write-back recorded the live UAL + WM stage on the artifact.
    assert len(publications) == 1
    assert publications[0]["dkg_stage"] == "wm"
    assert publications[0]["context_graph_id"] == "cg-1"
    assert publications[0]["publish_state"] == "written"
    assert publications[0]["ual"] == "agience://memory/cg-1/abc"


def test_governed_mode_rejects_draft_artifact(monkeypatch):
    """The governance gate: a draft artifact must not reach DKG."""

    def agience_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "art-002",
                "state": "draft",
                "title": "Half-baked",
                "type": "research-note",
                "content": "...",
            },
        )

    captured: Dict[str, Any] = {}
    _patch_agience(monkeypatch, agience_handler)
    _patch_dkg_memory_turn(monkeypatch, captured)
    monkeypatch.setenv("DKG_TOKEN", "dkg-tok")
    monkeypatch.setenv("AGIENCE_BASE_URL", "http://agience.test")

    result = runner.invoke(
        app,
        [
            "wm-write",
            "--context-graph-id", "cg-1",
            "--from-agience-artifact", "art-002",
        ],
    )

    assert result.exit_code == 2, result.output
    # The DKG memory_turn must NOT have been called for a draft.
    assert "request" not in captured
    combined = result.output + (result.stderr if hasattr(result, "stderr") else "")
    # Some Click/Typer versions write to stderr; fall back to checking exit code.
    assert result.exit_code == 2


def test_governed_mode_handles_unreachable_agience(monkeypatch):
    """Transport failures surface a clear non-governance error."""

    def agience_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="service unavailable")

    captured: Dict[str, Any] = {}
    _patch_agience(monkeypatch, agience_handler)
    _patch_dkg_memory_turn(monkeypatch, captured)
    monkeypatch.setenv("DKG_TOKEN", "dkg-tok")
    monkeypatch.setenv("AGIENCE_BASE_URL", "http://agience.test")

    result = runner.invoke(
        app,
        [
            "wm-write",
            "--context-graph-id", "cg-1",
            "--from-agience-artifact", "art-503",
        ],
    )

    assert result.exit_code == 3, result.output
    assert "request" not in captured


def test_explicit_overrides_take_precedence_over_agience(monkeypatch):
    """Explicit CLI options override values fetched from Agience."""

    def agience_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "art-001",
                "state": "committed",
                "title": "Original Title",
                "type": "decision",
                "content": "Original content.",
                "author": "Original Author",
            },
        )

    captured: Dict[str, Any] = {}
    _patch_agience(monkeypatch, agience_handler)
    _patch_dkg_memory_turn(monkeypatch, captured)
    monkeypatch.setenv("DKG_TOKEN", "dkg-tok")

    result = runner.invoke(
        app,
        [
            "wm-write",
            "--context-graph-id", "cg-1",
            "--from-agience-artifact", "art-001",
            "--title", "Overridden Title",
            "--author", "Overridden Author",
        ],
    )

    assert result.exit_code == 0, result.output
    req = captured["request"]
    assert req.title == "Overridden Title"
    assert req.author == "Overridden Author"
    # Non-overridden fields still come from Agience
    assert req.artifact_type == "decision"


def test_explicit_mode_still_works_without_governed_flag(monkeypatch):
    """Backwards compatibility: the original explicit-args path still works."""
    captured: Dict[str, Any] = {}
    _patch_dkg_memory_turn(monkeypatch, captured)
    monkeypatch.setenv("DKG_TOKEN", "dkg-tok")

    result = runner.invoke(
        app,
        [
            "wm-write",
            "--context-graph-id", "cg-1",
            "--title", "Direct Note",
            "--artifact-type", "research-note",
            "--artifact-id", "art-direct-1",
            "--content", "Body.",
        ],
    )

    assert result.exit_code == 0, result.output
    req = captured["request"]
    assert req.title == "Direct Note"
    assert req.commit_receipt_id is None  # No governance receipt in explicit mode


def test_explicit_mode_missing_required_fields_fails(monkeypatch):
    """Without --from-agience-artifact, core fields must be supplied."""
    monkeypatch.setenv("DKG_TOKEN", "dkg-tok")
    result = runner.invoke(
        app,
        [
            "wm-write",
            "--context-graph-id", "cg-1",
            # Missing --title, --artifact-type, --artifact-id, --content
        ],
    )
    assert result.exit_code == 1, result.output
    output = result.output + (getattr(result, "stderr", "") or "")
    # The error message hints at the governed-mode alternative
    assert "from-agience-artifact" in output or "missing" in output.lower()


# ---------------------------------------------------------------------------
# _ka_name_from_ref — promote/vm-publish KA-name resolution
# ---------------------------------------------------------------------------


def test_ka_name_from_ref_accepts_bare_name():
    """A plain KA name (as returned by wm-write) passes through unchanged."""
    from agience_dkg_integration.cli import _ka_name_from_ref

    name = "468dfefc-Architecture-Decision-Record-DKG-v10"
    assert _ka_name_from_ref(name) == name


def test_ka_name_from_ref_accepts_legacy_assertion_uri():
    """Legacy ``…/assertion/{addr}/{name}`` URIs yield their final segment."""
    from agience_dkg_integration.cli import _ka_name_from_ref

    ref = "did:dkg:context-graph:cg-1/assertion/0xabc/my-asset"
    assert _ka_name_from_ref(ref) == "my-asset"


def test_ka_name_from_ref_rejects_v10_turn_uri():
    """v10.0.1 WM/SWM/VM turnUris end in a revision index, not the KA name."""
    import typer

    from agience_dkg_integration.cli import _ka_name_from_ref

    turn_uri = "did:dkg:context-graph:agience-demo/_working_memory/0x7529/1"
    with pytest.raises(typer.BadParameter):
        _ka_name_from_ref(turn_uri)
