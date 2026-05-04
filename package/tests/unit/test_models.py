"""Unit tests for agience_dkg_integration models."""

from agience_dkg_integration.models import (
    AssertionPromoteRequest,
    AssertionPromoteResult,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryTurnRequest,
    MemoryTurnResult,
)


def test_memory_turn_request_defaults_to_wm():
    req = MemoryTurnRequest(contextGraphId="cg-1", markdown="**Title:** Test\n\nBody text.")
    assert req.layer == "wm"
    assert req.session_uri is None
    assert req.sub_graph_name is None


def test_memory_turn_request_accepts_swm():
    req = MemoryTurnRequest(contextGraphId="cg-1", markdown="body", layer="swm")
    assert req.layer == "swm"


def test_memory_turn_request_alias_access():
    req = MemoryTurnRequest(
        contextGraphId="cg-1",
        markdown="body",
        sessionUri="agience://collections/col-1",
    )
    assert req.context_graph_id == "cg-1"
    assert req.session_uri == "agience://collections/col-1"


def test_memory_turn_result_parses_turn_uri():
    result = MemoryTurnResult(turnUri="agience://wm/turn/abc123", layer="wm", contextGraphId="cg-1", raw_response={})
    assert result.turn_uri == "agience://wm/turn/abc123"
    assert result.layer == "wm"


def test_assertion_promote_request_entities_default_empty():
    req = AssertionPromoteRequest(name="abc123", contextGraphId="cg-1")
    assert req.entities == []
    assert req.name == "abc123"
    assert req.context_graph_id == "cg-1"


def test_assertion_promote_result_ok():
    result = AssertionPromoteResult(ok=True, name="abc123", raw_response={"status": "promoted"})
    assert result.ok is True
    assert result.name == "abc123"


def test_memory_search_request_defaults():
    req = MemorySearchRequest(contextGraphId="cg-1", query="research note")
    assert req.limit == 20
    assert req.memory_layers is None


def test_memory_search_request_with_layers():
    req = MemorySearchRequest(contextGraphId="cg-1", query="q", memoryLayers=["wm", "swm"])
    assert req.memory_layers == ["wm", "swm"]


def test_memory_search_result_defaults():
    result = MemorySearchResult(raw_response={})
    assert result.result_count == 0
    assert result.results == []
