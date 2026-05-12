"""Agience Core client — governed-mode source of truth for DKG projection.

This module enforces the "governance layer" claim of this integration in code,
not just documentation. When a caller writes to DKG via `--from-agience-artifact`,
the artifact is fetched from a running Agience instance and rejected unless it
has reached the `committed` state — that is, it has passed Agience's
human-review commit boundary and produced a `CommitReceipt`.

This is what `dkg mcp setup` cannot do on its own: any agent connected over
plain MCP can `dkg-create` arbitrary content. The governed-mode path here
refuses to project anything that has not been committed in Agience.

Environment variables:
    AGIENCE_BASE_URL          Base URL of the Agience backend (default
                              http://localhost:8081).
    AGIENCE_TOKEN             Bearer token for the Agience API. Optional —
                              omit for unauthenticated dev instances.
    AGIENCE_ARTIFACT_ENDPOINT Path template for fetching an artifact
                              (default `/artifacts/{artifact_id}`).
                              `{artifact_id}` is replaced with the id.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field


class AgienceClientError(RuntimeError):
    """Base exception for Agience client failures (transport, auth, parse)."""


class ArtifactNotCommittedError(AgienceClientError):
    """Raised when a caller attempts to project a non-committed artifact.

    The integration refuses to write uncommitted (draft / archived / unknown)
    artifacts to DKG. This is the load-bearing check for the governance claim.
    """

    def __init__(self, artifact_id: str, state: str) -> None:
        self.artifact_id = artifact_id
        self.state = state
        super().__init__(
            f"Artifact '{artifact_id}' is in state '{state}', not 'committed'. "
            "Only committed Agience artifacts may be projected to DKG."
        )


class AgienceArtifact(BaseModel):
    """A typed view of an Agience artifact for DKG projection.

    Field names are the Agience canonical forms; the integration maps these
    onto DKG `agience:` JSON-LD predicates in `client.py`.
    """

    id: str
    state: str = Field(description="One of: draft, committed, archived")
    title: str = ""
    artifact_type: str = Field(default="artifact", alias="type")
    content: str = ""
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    collection_id: Optional[str] = None
    commit_receipt_id: Optional[str] = None
    commit_receipt: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True}


class AgienceClient:
    """Synchronous Agience Core HTTP client (read-only).

    Only fetches artifacts. Never writes back to Agience. The integration
    package is a one-way bridge from Agience's governed authoring surface
    into DKG memory layers.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        bearer_token: Optional[str] = None,
        artifact_endpoint: Optional[str] = None,
        *,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get(
            "AGIENCE_BASE_URL", "http://localhost:8081"
        )).rstrip("/")
        self._bearer_token = bearer_token or os.environ.get("AGIENCE_TOKEN", "")
        self.artifact_endpoint = artifact_endpoint or os.environ.get(
            "AGIENCE_ARTIFACT_ENDPOINT", "/artifacts/{artifact_id}"
        )
        self._timeout = timeout

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self._bearer_token:
            h["Authorization"] = f"Bearer {self._bearer_token}"
        return h

    def _artifact_url(self, artifact_id: str) -> str:
        path = self.artifact_endpoint.format(artifact_id=artifact_id)
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def get_artifact(self, artifact_id: str) -> AgienceArtifact:
        """Fetch an artifact from Agience without enforcing commit state.

        Use `get_committed_artifact()` for governed-mode projection where
        only committed artifacts are acceptable.
        """
        url = self._artifact_url(artifact_id)
        try:
            with httpx.Client(timeout=self._timeout) as http:
                r = http.get(url, headers=self._headers())
        except httpx.HTTPError as exc:
            raise AgienceClientError(
                f"Failed to reach Agience at {url}: {exc}"
            ) from exc

        if r.status_code == 404:
            raise AgienceClientError(f"Artifact '{artifact_id}' not found in Agience")
        if r.status_code == 401 or r.status_code == 403:
            raise AgienceClientError(
                f"Agience refused the request ({r.status_code}). "
                "Check AGIENCE_TOKEN."
            )
        if r.status_code >= 400:
            raise AgienceClientError(
                f"Agience returned {r.status_code} for {artifact_id}: {r.text[:200]}"
            )

        try:
            return AgienceArtifact.model_validate(r.json())
        except Exception as exc:
            raise AgienceClientError(
                f"Could not parse Agience artifact response: {exc}"
            ) from exc

    def get_committed_artifact(self, artifact_id: str) -> AgienceArtifact:
        """Fetch an artifact and enforce that it has been committed.

        Raises:
            ArtifactNotCommittedError: if the artifact's state is not
                'committed'. This is the governance gate that prevents
                draft or archived content from reaching DKG.
            AgienceClientError: for transport, auth, or parse failures.
        """
        artifact = self.get_artifact(artifact_id)
        if artifact.state != "committed":
            raise ArtifactNotCommittedError(artifact_id, artifact.state)
        return artifact
