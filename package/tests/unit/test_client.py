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
    turn_response = {"turnUri": "agience://wm/turn/abc123", "layer": "wm", "contextGraphId": "cg-1"}

    def fake_post(self_inner, url, *, headers, json, **kwargs):
        assert "/api/memory/turn" in url
        assert json["contextGraphId"] == "cg-1"
        assert json["layer"] == "wm"
        assert "markdown" in json

        class FakeResp:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return turn_response

        return FakeResp()

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="tok")
    result = client.memory_turn(MemoryTurnRequest(contextGraphId="cg-1", markdown="**Title:** T\n\nBody"))
    assert result.turn_uri == "agience://wm/turn/abc123"
    assert result.layer == "wm"


def test_assertion_promote_calls_correct_endpoint(monkeypatch):
    promote_response = {"status": "promoted"}
    captured = {}

    def fake_post(self_inner, url, *, headers, json, **kwargs):
        captured["url"] = url
        captured["body"] = json

        class FakeResp:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return promote_response

        return FakeResp()

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="tok")
    result = client.assertion_promote(
        AssertionPromoteRequest(name="abc123", contextGraphId="cg-1")
    )
    assert "/api/assertion/abc123/promote" in captured["url"]
    assert captured["body"]["contextGraphId"] == "cg-1"
    assert result.ok is True
    assert result.name == "abc123"


def test_memory_search_sends_correct_body(monkeypatch):
    search_response = {"resultCount": 2, "results": [{"id": "r1"}, {"id": "r2"}]}
    captured = {}

    def fake_post(self_inner, url, *, headers, json, **kwargs):
        captured["url"] = url
        captured["body"] = json

        class FakeResp:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return search_response

        return FakeResp()

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="tok")
    result = client.memory_search(
        MemorySearchRequest(contextGraphId="cg-1", query="research note", limit=5, memoryLayers=["wm"])
    )
    assert "/api/memory/search" in captured["url"]
    assert captured["body"]["query"] == "research note"
    assert captured["body"]["limit"] == 5
    assert captured["body"]["memoryLayers"] == ["wm"]
    assert result.result_count == 2
    assert len(result.results) == 2


def test_authorization_header_sent(monkeypatch):
    captured_headers = {}

    def fake_post(self_inner, url, *, headers, json, **kwargs):
        captured_headers.update(headers)

        class FakeResp:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return {"turnUri": "x", "layer": "wm"}

        return FakeResp()

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    client = DkgHttpClient(base_url="http://localhost:8081", bearer_token="my-secret-token")
    client.memory_turn(MemoryTurnRequest(contextGraphId="cg-1", markdown="body"))
    assert captured_headers.get("Authorization") == "Bearer my-secret-token"
