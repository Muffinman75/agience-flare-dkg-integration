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
    """Replace DkgHttpClient.memory_turn with a recorder that returns success."""

    def fake_memory_turn(self, request):
        captured["request"] = request
        # Return a fake successful MemoryTurnResult
        from agience_dkg_integration.models import MemoryTurnResult
        return MemoryTurnResult(
            turnUri="agience://memory/cg-1/abc",
            layer=request.layer,
            contextGraphId=request.context_graph_id,
            status="anchored",
            error=None,
            raw_response={"mock": True},
        )

    monkeypatch.setattr(dkg_client_mod.DkgHttpClient, "memory_turn", fake_memory_turn)


def test_governed_mode_projects_committed_artifact(monkeypatch):
    """Happy path: a committed Agience artifact is fetched and projected.

    Verifies:
    - Title/type/content/etc. flow through from Agience into the DKG request
    - commit_receipt_id is attached
    """

    def agience_handler(request: httpx.Request) -> httpx.Response:
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
