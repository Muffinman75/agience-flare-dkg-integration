"""Unit tests for the Agience Core client and the governed-mode contract.

These tests are the load-bearing proof that the integration enforces
governance in code, not just documentation. A draft / archived / unknown
artifact MUST be rejected before reaching DKG.
"""

from __future__ import annotations

import httpx
import pytest

from agience_dkg_integration.agience_client import (
    AgienceArtifact,
    AgienceClient,
    AgienceClientError,
    ArtifactNotCommittedError,
)


def _client_with_transport(handler) -> AgienceClient:
    """Build an AgienceClient that routes through a mock transport.

    Patches httpx.Client to inject the transport at construction time.
    """
    client = AgienceClient(
        base_url="http://agience.test", bearer_token="test-token"
    )
    transport = httpx.MockTransport(handler)
    original_client_cls = httpx.Client

    class _PatchedClient(original_client_cls):  # type: ignore[misc]
        def __init__(self, *args, **kwargs):
            kwargs.pop("transport", None)
            super().__init__(*args, transport=transport, **kwargs)

    client._http_client_cls = _PatchedClient  # type: ignore[attr-defined]
    return client


@pytest.fixture
def patched_httpx(monkeypatch):
    """Yield a helper that replaces httpx.Client with a MockTransport-backed one."""

    def _install(handler):
        transport = httpx.MockTransport(handler)
        original = httpx.Client

        def _factory(*args, **kwargs):
            kwargs.pop("transport", None)
            return original(*args, transport=transport, **kwargs)

        monkeypatch.setattr("agience_dkg_integration.agience_client.httpx.Client", _factory)

    return _install


def test_get_committed_artifact_returns_artifact(patched_httpx):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/artifacts/art-001"
        assert request.headers["Authorization"] == "Bearer test-token"
        return httpx.Response(
            200,
            json={
                "id": "art-001",
                "state": "committed",
                "title": "Architecture Decision",
                "type": "architecture-decision",
                "content": "Use DKG v10 as the shared substrate.",
                "author": "Manoj",
                "tags": ["architecture", "dkg-v10"],
                "collection_id": "agience-architecture",
                "commit_receipt_id": "rcpt-abc",
            },
        )

    patched_httpx(handler)
    client = AgienceClient(base_url="http://agience.test", bearer_token="test-token")
    artifact = client.get_committed_artifact("art-001")

    assert isinstance(artifact, AgienceArtifact)
    assert artifact.id == "art-001"
    assert artifact.state == "committed"
    assert artifact.artifact_type == "architecture-decision"
    assert artifact.author == "Manoj"
    assert artifact.tags == ["architecture", "dkg-v10"]
    assert artifact.collection_id == "agience-architecture"
    assert artifact.commit_receipt_id == "rcpt-abc"


def test_get_committed_artifact_rejects_draft(patched_httpx):
    """The governance gate: a draft artifact must NOT reach DKG."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "art-002",
                "state": "draft",
                "title": "Half-baked thoughts",
                "type": "research-note",
                "content": "...",
            },
        )

    patched_httpx(handler)
    client = AgienceClient(base_url="http://agience.test", bearer_token="test-token")

    with pytest.raises(ArtifactNotCommittedError) as excinfo:
        client.get_committed_artifact("art-002")

    assert excinfo.value.artifact_id == "art-002"
    assert excinfo.value.state == "draft"
    assert "draft" in str(excinfo.value)
    assert "committed" in str(excinfo.value)


def test_get_committed_artifact_rejects_archived(patched_httpx):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"id": "art-003", "state": "archived", "type": "decision"},
        )

    patched_httpx(handler)
    client = AgienceClient(base_url="http://agience.test", bearer_token="test-token")

    with pytest.raises(ArtifactNotCommittedError):
        client.get_committed_artifact("art-003")


def test_404_raises_clear_error(patched_httpx):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    patched_httpx(handler)
    client = AgienceClient(base_url="http://agience.test")

    with pytest.raises(AgienceClientError) as excinfo:
        client.get_committed_artifact("does-not-exist")

    assert "not found" in str(excinfo.value).lower()


def test_401_surfaces_auth_failure(patched_httpx):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    patched_httpx(handler)
    client = AgienceClient(base_url="http://agience.test", bearer_token="bad")

    with pytest.raises(AgienceClientError) as excinfo:
        client.get_artifact("art-001")

    assert "AGIENCE_TOKEN" in str(excinfo.value)


def test_no_token_means_no_auth_header(patched_httpx):
    """When no token is configured, no Authorization header is sent."""
    received_headers: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        received_headers.update(request.headers)
        return httpx.Response(
            200,
            json={"id": "art-x", "state": "committed", "type": "claim"},
        )

    patched_httpx(handler)
    client = AgienceClient(base_url="http://agience.test")
    client.get_artifact("art-x")

    assert "authorization" not in {k.lower() for k in received_headers}


def test_endpoint_template_is_configurable(patched_httpx):
    seen_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        return httpx.Response(
            200,
            json={"id": "art-001", "state": "committed", "type": "claim"},
        )

    patched_httpx(handler)
    client = AgienceClient(
        base_url="http://agience.test",
        artifact_endpoint="/v2/governed/artifact/{artifact_id}/full",
    )
    client.get_artifact("art-001")

    assert seen_paths == ["/v2/governed/artifact/art-001/full"]


def test_env_var_defaults(monkeypatch, patched_httpx):
    monkeypatch.setenv("AGIENCE_BASE_URL", "http://env-host:9000")
    monkeypatch.setenv("AGIENCE_TOKEN", "env-token")

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["host"] = request.url.host
        captured["port"] = request.url.port
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={"id": "art-1", "state": "committed", "type": "claim"},
        )

    patched_httpx(handler)
    client = AgienceClient()
    client.get_committed_artifact("art-1")

    assert captured["host"] == "env-host"
    assert captured["port"] == 9000
    assert captured["auth"] == "Bearer env-token"


def test_invalid_json_raises(patched_httpx):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json at all")

    patched_httpx(handler)
    client = AgienceClient(base_url="http://agience.test")

    with pytest.raises(AgienceClientError):
        client.get_artifact("art-1")
