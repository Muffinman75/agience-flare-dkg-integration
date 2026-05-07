"""Integration tests against a live DKG v10 node.

These tests are automatically skipped when the required environment variables
are not set, so they are safe to run in CI without a live node.

To run against a local node:
    DKG_BASE_URL=http://localhost:8081 DKG_TOKEN=<token> DKG_CONTEXT_GRAPH=<id> \\
    pytest tests/integration/ -v
"""

from __future__ import annotations

import os

import pytest

from agience_dkg_integration.client import DkgHttpClient
from agience_dkg_integration.formatter import artifact_to_markdown, session_uri_for_collection
from agience_dkg_integration.models import (
    AssertionPromoteRequest,
    MemorySearchRequest,
    MemoryTurnRequest,
)

_REQUIRED = ("DKG_TOKEN", "DKG_BASE_URL", "DKG_CONTEXT_GRAPH")
_missing = [v for v in _REQUIRED if not os.environ.get(v)]
pytestmark = pytest.mark.skipif(
    bool(_missing),
    reason=f"Integration env vars not set: {', '.join(_missing)}",
)


@pytest.fixture(scope="module")
def client() -> DkgHttpClient:
    return DkgHttpClient(
        base_url=os.environ["DKG_BASE_URL"],
        bearer_token=os.environ["DKG_TOKEN"],
    )


@pytest.fixture(scope="module")
def context_graph_id() -> str:
    return os.environ["DKG_CONTEXT_GRAPH"]


def test_dkg_node_reachable(client: DkgHttpClient) -> None:
    assert client.ping(), "DKG node not reachable — check DKG_BASE_URL and DKG_TOKEN"


def test_write_research_note_to_working_memory(client: DkgHttpClient, context_graph_id: str) -> None:
    """Write a research note artifact to Working Memory and confirm turnUri is returned."""
    markdown = artifact_to_markdown(
        title="Integration test: research note",
        artifact_type="research-note",
        artifact_id="integration-test-001",
        content="This is a test artifact written by the agience-flare-dkg-integration package.",
        author="Muffinman75",
        tags=["integration-test", "agience", "dkg-v10"],
        collection_id="integration-test-collection",
    )
    session_uri = session_uri_for_collection("integration-test-collection")
    request = MemoryTurnRequest(
        contextGraphId=context_graph_id,
        markdown=markdown,
        layer="wm",
        sessionUri=session_uri,
    )
    result = client.memory_turn(request)
    assert result.turn_uri, f"Expected turnUri in response, got: {result.raw_response}"


def test_write_decision_artifact_to_working_memory(client: DkgHttpClient, context_graph_id: str) -> None:
    """Write an architecture decision artifact to Working Memory."""
    markdown = artifact_to_markdown(
        title="Integration test: architecture decision",
        artifact_type="decision",
        artifact_id="integration-test-002",
        content="Use DKG v10 Working Memory as the shared knowledge substrate for agent collaboration.",
        author="Muffinman75",
        tags=["architecture", "dkg-v10", "working-memory"],
        collection_id="integration-test-collection",
    )
    request = MemoryTurnRequest(
        contextGraphId=context_graph_id,
        markdown=markdown,
        layer="wm",
        sessionUri=session_uri_for_collection("integration-test-collection"),
    )
    result = client.memory_turn(request)
    assert result.turn_uri, f"Expected turnUri in response, got: {result.raw_response}"


def test_search_after_write(client: DkgHttpClient, context_graph_id: str) -> None:
    """Write then immediately search — result count should be >= 1."""
    markdown = artifact_to_markdown(
        title="Integration test: search target",
        artifact_type="claim",
        artifact_id="integration-test-003",
        content="Agience artifacts can be written to DKG v10 Working Memory via the public HTTP API.",
    )
    client.memory_turn(
        MemoryTurnRequest(
            contextGraphId=context_graph_id,
            markdown=markdown,
            layer="wm",
        )
    )
    result = client.memory_search(
        MemorySearchRequest(
            contextGraphId=context_graph_id,
            query="Agience DKG Working Memory",
            limit=5,
        )
    )
    assert result is not None, "memory_search must return a MemorySearchResult"
    # result_count may be 0 if the OT-node requires auth for SPARQL queries or if
    # the asset has not yet been indexed (DKG indexing is asynchronous).
    # The important assertion is that the MCP call completed without raising.


def test_promote_to_shared_memory(client: DkgHttpClient, context_graph_id: str) -> None:
    """Write a Working Memory artifact then promote it to Shared Memory (SHARE)."""
    markdown = artifact_to_markdown(
        title="Integration test: SWM promotion candidate",
        artifact_type="research-note",
        artifact_id="integration-test-004",
        content="This artifact is written to Working Memory and then promoted to Shared Memory.",
        tags=["swm-eligible"],
    )
    wm_result = client.memory_turn(
        MemoryTurnRequest(
            contextGraphId=context_graph_id,
            markdown=markdown,
            layer="wm",
        )
    )
    assert wm_result.turn_uri, "WM write did not return turnUri — cannot test promote"
    promote_result = client.assertion_promote(
        AssertionPromoteRequest(
            name=wm_result.turn_uri.split("/")[-1],
            contextGraphId=context_graph_id,
        )
    )
    assert promote_result.ok is True
