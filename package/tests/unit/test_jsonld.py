"""Unit tests for typed agience: JSON-LD Knowledge Asset generation."""

import json

import pytest

from agience_dkg_integration.client import DkgHttpClient
from agience_dkg_integration.models import MemoryTurnRequest


def _capture_jsonld(monkeypatch, **request_kwargs):
    """Helper: patch _mcp_call_tool, call memory_turn, return the parsed JSON-LD."""
    captured = {}

    def fake_mcp_call_tool(self_inner, tool_name, arguments):
        captured["tool"] = tool_name
        captured["args"] = arguments
        return {
            "result": {
                "content": [
                    {"type": "text", "text": "Knowledge Asset created.\n\nUAL: did:dkg:otp:20430/0xtest/1/1"}
                ]
            }
        }

    monkeypatch.setattr(
        "agience_dkg_integration.client.DkgHttpClient._mcp_call_tool",
        fake_mcp_call_tool,
    )
    client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="tok")
    request = MemoryTurnRequest(**request_kwargs)
    client.memory_turn(request)

    jsonld = json.loads(captured["args"]["jsonld"])
    return jsonld, captured


class TestTypedJsonLd:
    """Verify the agience: RDF vocabulary in generated JSON-LD."""

    def test_context_includes_agience_namespace(self, monkeypatch):
        jsonld, _ = _capture_jsonld(
            monkeypatch,
            contextGraphId="test-cg",
            markdown="body",
            artifactType="decision",
            artifactId="art-001",
        )
        ctx = jsonld["@context"]
        assert ctx["agience"] == "https://agience.ai/ontology/"
        assert ctx["schema"] == "https://schema.org/"

    def test_type_uses_agience_prefix(self, monkeypatch):
        jsonld, _ = _capture_jsonld(
            monkeypatch,
            contextGraphId="test-cg",
            markdown="body",
            artifactType="research-note",
            artifactId="art-002",
        )
        assert jsonld["@type"] == "agience:research-note"

    def test_id_includes_context_graph_and_artifact(self, monkeypatch):
        jsonld, _ = _capture_jsonld(
            monkeypatch,
            contextGraphId="my-cg",
            markdown="body",
            artifactType="claim",
            artifactId="claim-42",
        )
        assert jsonld["@id"] == "agience:my-cg/claim-42"

    def test_agience_predicates_present(self, monkeypatch):
        jsonld, _ = _capture_jsonld(
            monkeypatch,
            contextGraphId="cg",
            markdown="body",
            artifactType="decision",
            artifactId="d1",
            title="My Decision",
            author="Alice",
            tags=["arch", "dkg"],
            collectionId="project-x",
        )
        assert jsonld["agience:contextGraphId"] == "cg"
        assert jsonld["agience:memoryLayer"] == "wm"
        assert jsonld["agience:artifactId"] == "d1"
        assert jsonld["agience:author"] == "Alice"
        assert jsonld["agience:tags"] == ["arch", "dkg"]
        assert jsonld["agience:collection"] == "project-x"
        assert jsonld["schema:name"] == "My Decision"

    def test_optional_fields_omitted_when_empty(self, monkeypatch):
        jsonld, _ = _capture_jsonld(
            monkeypatch,
            contextGraphId="cg",
            markdown="body",
        )
        assert "agience:author" not in jsonld
        assert "agience:tags" not in jsonld
        assert "agience:collection" not in jsonld

    def test_session_uri_mapped_to_schema_isPartOf(self, monkeypatch):
        jsonld, _ = _capture_jsonld(
            monkeypatch,
            contextGraphId="cg",
            markdown="body",
            sessionUri="agience://collections/my-project",
        )
        assert jsonld["schema:isPartOf"] == "agience://collections/my-project"

    def test_swm_layer_sets_public_privacy(self, monkeypatch):
        _, captured = _capture_jsonld(
            monkeypatch,
            contextGraphId="cg",
            markdown="body",
            layer="swm",
        )
        assert captured["args"]["privacy"] == "public"

    def test_wm_layer_sets_private_privacy(self, monkeypatch):
        _, captured = _capture_jsonld(
            monkeypatch,
            contextGraphId="cg",
            markdown="body",
            layer="wm",
        )
        assert captured["args"]["privacy"] == "private"


class TestErrorStatus:
    """Verify status/error fields in MemoryTurnResult."""

    def test_successful_result_has_anchored_status(self, monkeypatch):
        def fake(self_inner, tool_name, args):
            return {"result": {"content": [{"type": "text", "text": "UAL: did:dkg:otp:20430/0xabc/1/1"}]}}

        monkeypatch.setattr(
            "agience_dkg_integration.client.DkgHttpClient._mcp_call_tool", fake
        )
        client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="tok")
        result = client.memory_turn(MemoryTurnRequest(contextGraphId="cg", markdown="body"))
        assert result.status == "anchored"
        assert result.error is None

    def test_connection_error_has_pending_status(self, monkeypatch):
        def fake(self_inner, tool_name, args):
            return {"result": {"content": [{"type": "text", "text": "CONNECTION ERROR: Couldn't connect to node"}]}}

        monkeypatch.setattr(
            "agience_dkg_integration.client.DkgHttpClient._mcp_call_tool", fake
        )
        client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="tok")
        result = client.memory_turn(MemoryTurnRequest(contextGraphId="cg", markdown="body"))
        assert result.status == "pending"
        assert "blockchain anchoring failed" in result.error
        assert "testnet RPC" in result.error

    def test_safe_mode_error_detected(self, monkeypatch):
        def fake(self_inner, tool_name, args):
            return {"result": {"content": [{"type": "text", "text": "Safe mode validation error"}]}}

        monkeypatch.setattr(
            "agience_dkg_integration.client.DkgHttpClient._mcp_call_tool", fake
        )
        client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="tok")
        result = client.memory_turn(MemoryTurnRequest(contextGraphId="cg", markdown="body"))
        assert result.status == "pending"
        assert "safe mode" in result.error.lower()
