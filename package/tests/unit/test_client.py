"""Unit tests for DkgHttpClient using httpx mock transport."""

import json

import httpx
import pytest

from agience_dkg_integration.client import DkgHttpClient
from agience_dkg_integration.models import (
    AssertionPromoteRequest,
    MemorySearchRequest,
    MemoryTurnRequest,
)


def _mock_transport(responses: dict) -> httpx.MockTransport:
    """Build a MockTransport from a {url_path: (status, body)} dict."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        status, body = responses.get(path, (404, {}))
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


def _client_with_transport(transport: httpx.MockTransport) -> DkgHttpClient:
    client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="test-token")
    client._transport = transport
    return client


class PatchedDkgHttpClient(DkgHttpClient):
    """Subclass that injects a mock transport into every httpx.Client call."""

    def __init__(self, responses: dict, **kwargs):
        super().__init__(**kwargs)
        self._responses = responses

    def _make_http_client(self, timeout: float) -> httpx.Client:
        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            status, body = self._responses.get(path, (404, {}))
            return httpx.Response(status, json=body)
        return httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout)


def _patched(responses: dict) -> PatchedDkgHttpClient:
    return PatchedDkgHttpClient(
        responses=responses,
        base_url="http://localhost:8081",
        bearer_token="test-token",
    )


def test_memory_turn_returns_turn_uri(monkeypatch):
    mcp_response = {"result": {"content": [{"type": "text", "text": "Knowledge Asset collection successfully created.\n\nUAL: did:dkg:otp:20430/0xabc/1/1\nDKG Explorer link: https://dkg-explorer.example"}]}}
    captured = {}

    def fake_mcp_call_tool(self_inner, tool_name, arguments):
        captured["tool"] = tool_name
        captured["args"] = arguments
        return mcp_response

    monkeypatch.setattr("agience_dkg_integration.client.DkgHttpClient._mcp_call_tool", fake_mcp_call_tool)
    client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="tok")
    result = client.memory_turn(MemoryTurnRequest(contextGraphId="cg-1", markdown="**Title:** T\n\nBody"))
    assert captured["tool"] == "dkg-create"
    assert captured["args"]["privacy"] == "private"
    assert "cg-1" in captured["args"]["jsonld"]
    assert result.turn_uri == "did:dkg:otp:20430/0xabc/1/1"
    assert result.layer == "wm"


def test_assertion_promote_calls_correct_endpoint(monkeypatch):
    mcp_response = {"result": {"content": [{"type": "text", "text": "Knowledge Asset collection successfully created.\n\nUAL: did:dkg:otp:20430/0xabc/1/2\nDKG Explorer link: https://dkg-explorer.example"}]}}
    captured = {}

    def fake_mcp_call_tool(self_inner, tool_name, arguments):
        captured["tool"] = tool_name
        captured["args"] = arguments
        return mcp_response

    monkeypatch.setattr("agience_dkg_integration.client.DkgHttpClient._mcp_call_tool", fake_mcp_call_tool)
    client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="tok")
    result = client.assertion_promote(
        AssertionPromoteRequest(name="abc123", contextGraphId="cg-1")
    )
    assert captured["tool"] == "dkg-create"
    assert captured["args"]["privacy"] == "public"
    assert "abc123" in captured["args"]["jsonld"]
    assert result.ok is True
    assert result.name == "abc123"


def test_memory_search_sends_correct_body(monkeypatch):
    mcp_response = {"result": {"content": [{"type": "text", "text": '✅ Query executed successfully\n\n**Results:**\n```json\n{"data": [{"s": "x", "text": "r1"}, {"s": "y", "text": "r2"}]}\n```'}]}}
    captured = {}

    def fake_mcp_call_tool(self_inner, tool_name, arguments):
        captured["tool"] = tool_name
        captured["args"] = arguments
        return mcp_response

    monkeypatch.setattr("agience_dkg_integration.client.DkgHttpClient._mcp_call_tool", fake_mcp_call_tool)
    client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="tok")
    result = client.memory_search(
        MemorySearchRequest(contextGraphId="cg-1", query="research note", limit=5, memoryLayers=["wm"])
    )
    assert captured["tool"] == "dkg-sparql-query"
    assert "research note" in captured["args"]["query"]
    assert "cg-1" in captured["args"]["query"]


def test_authorization_header_included(monkeypatch):
    """Verify the bearer token is included in request headers."""
    client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="my-secret-token")
    headers = client._headers()
    assert headers["Authorization"] == "Bearer my-secret-token"


def test_authorization_header_with_session_id(monkeypatch):
    """Verify the mcp-session-id header is included when provided."""
    client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="tok")
    headers = client._headers(session_id="sess-42")
    assert headers["mcp-session-id"] == "sess-42"
    assert headers["Authorization"] == "Bearer tok"
