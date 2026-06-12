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


def _is_wsl() -> bool:
    """Detect whether the current process is running under WSL2."""
    try:
        with open("/proc/version", "r", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def _wsl_loopback_hint(url: str) -> str:
    """Return an actionable hint when a localhost call is likely hitting the
    WSL2 loopback rather than the Windows host where Agience runs.

    WSL2's ``localhost`` resolves to WSL's own loopback interface, *not* the
    Windows host. Services running on Windows (e.g. Agience on :8081) are
    only reachable from WSL via the Windows host IP, which is exposed via
    the default gateway.
    """
    if not _is_wsl():
        return ""
    if not any(host in url for host in ("localhost", "127.0.0.1")):
        return ""
    try:
        with open("/proc/net/route", "r", encoding="utf-8") as f:
            lines = f.read().splitlines()[1:]
        for line in lines:
            parts = line.split()
            if len(parts) < 3:
                continue
            if parts[1] == "00000000":  # default route
                # Gateway is little-endian hex
                hex_ip = parts[2]
                ip = ".".join(str(int(hex_ip[i : i + 2], 16)) for i in (6, 4, 2, 0))
                return (
                    f"\n\nHint: this process is running in WSL2 but the URL targets "
                    f"a localhost/loopback address. The Agience backend appears to run "
                    f"on the Windows host \u2014 try AGIENCE_BASE_URL=http://{ip}:8081 "
                    f"(your Windows host IP). Add `--agience-base-url http://{ip}:8081` "
                    f"or export AGIENCE_BASE_URL in your shell."
                )
    except OSError:
        pass
    return (
        "\n\nHint: this process is running in WSL2 but the URL targets a "
        "localhost address. WSL2's localhost is not the Windows host; "
        "set AGIENCE_BASE_URL to the Windows host IP "
        "(e.g. `$(ip route show | awk '/default/ {print $3}')`)."
    )


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
    """Synchronous Agience Core HTTP client.

    Primarily a read path: it fetches committed artifacts as the governed
    source of truth for DKG projection. The single exception is
    :meth:`record_publication`, which writes one provenance receipt back to
    Agience after a successful DKG ``wm-write`` / ``promote`` so the platform's
    DKG Projection panel can display the real UAL and stage. That write-back is
    always best-effort and never gates the DKG operation itself.
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

    def _publication_url(self, artifact_id: str) -> str:
        return f"{self._artifact_url(artifact_id)}/dkg/publication"

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
            hint = _wsl_loopback_hint(url)
            raise AgienceClientError(
                f"Failed to reach Agience at {url}: {exc}{hint}"
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

    def record_publication(
        self,
        artifact_id: str,
        *,
        dkg_stage: str,
        context_graph_id: str,
        publish_state: str,
        ual: Optional[str] = None,
        assertion_id: Optional[str] = None,
        turn_uri: Optional[str] = None,
        transport: Optional[str] = None,
        projection_mode: str = "rdf",
        content_digest: Optional[str] = None,
        remote_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Write back a DKG publication receipt (the real projection outcome).

        This is the only write this client performs. It lets the Agience DKG
        Projection panel show the live UAL and stage state for a governed
        artifact. Callers treat failures as non-fatal: the DKG write has
        already succeeded by the time this is invoked.

        Raises:
            AgienceClientError: on transport / auth / HTTP failure, so the
                caller can warn without aborting.
        """
        url = self._publication_url(artifact_id)
        payload: Dict[str, Any] = {
            "dkg_stage": dkg_stage,
            "context_graph_id": context_graph_id,
            "publish_state": publish_state,
            "projection_mode": projection_mode,
        }
        for key, value in (
            ("ual", ual),
            ("assertion_id", assertion_id),
            ("turn_uri", turn_uri),
            ("transport", transport),
            ("content_digest", content_digest),
            ("remote_timestamp", remote_timestamp),
        ):
            if value:
                payload[key] = value

        try:
            with httpx.Client(timeout=self._timeout) as http:
                r = http.post(url, headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            hint = _wsl_loopback_hint(url)
            raise AgienceClientError(
                f"Failed to record publication at {url}: {exc}{hint}"
            ) from exc

        if r.status_code >= 400:
            raise AgienceClientError(
                f"Agience returned {r.status_code} recording publication for "
                f"{artifact_id}: {r.text[:200]}"
            )
        try:
            return r.json()
        except Exception:
            return {}

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
