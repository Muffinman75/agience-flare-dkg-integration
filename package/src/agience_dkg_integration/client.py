from __future__ import annotations

from typing import Any, Dict

import httpx

from .models import (
    AssertionPromoteRequest,
    AssertionPromoteResult,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryTurnRequest,
    MemoryTurnResult,
)


class DkgHttpClient:
    """Thin synchronous wrapper around the DKG v10 node HTTP API (port 8081).

    All methods raise httpx.HTTPStatusError on non-2xx responses.
    Credentials are read from constructor arguments; never hardcoded.
    """

    def __init__(
        self,
        base_url: str,
        bearer_token: str,
        *,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._bearer_token = bearer_token
        self._timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._bearer_token}",
            "Content-Type": "application/json",
        }

    def ping(self) -> bool:
        """Return True if the node is reachable and the token is valid."""
        try:
            with httpx.Client(timeout=5.0) as http:
                r = http.get(f"{self.base_url}/api/agents", headers=self._headers())
                return r.status_code == 200
        except Exception:
            return False

    def memory_turn(self, request: MemoryTurnRequest) -> MemoryTurnResult:
        """Write a Knowledge Asset to Working Memory (or Shared Memory) via POST /api/memory/turn."""
        body: Dict[str, Any] = {
            "contextGraphId": request.context_graph_id,
            "markdown": request.markdown,
            "layer": request.layer,
        }
        if request.session_uri:
            body["sessionUri"] = request.session_uri
        if request.sub_graph_name:
            body["subGraphName"] = request.sub_graph_name

        with httpx.Client(timeout=self._timeout) as http:
            r = http.post(
                f"{self.base_url}/api/memory/turn",
                headers=self._headers(),
                json=body,
            )
            r.raise_for_status()
            raw = r.json()

        return MemoryTurnResult(
            turn_uri=raw.get("turnUri"),
            layer=raw.get("layer"),
            context_graph_id=raw.get("contextGraphId"),
            raw_response=raw,
        )

    def assertion_promote(self, request: AssertionPromoteRequest) -> AssertionPromoteResult:
        """Promote a Working Memory assertion to Shared Memory (SHARE) via POST /api/assertion/:name/promote."""
        body: Dict[str, Any] = {"contextGraphId": request.context_graph_id}
        if request.entities:
            body["entities"] = request.entities

        with httpx.Client(timeout=self._timeout) as http:
            r = http.post(
                f"{self.base_url}/api/assertion/{request.name}/promote",
                headers=self._headers(),
                json=body,
            )
            r.raise_for_status()
            raw = r.json()

        return AssertionPromoteResult(ok=True, name=request.name, raw_response=raw)

    def memory_search(self, request: MemorySearchRequest) -> MemorySearchResult:
        """Search Working and/or Shared Memory via POST /api/memory/search."""
        body: Dict[str, Any] = {
            "contextGraphId": request.context_graph_id,
            "query": request.query,
            "limit": request.limit,
        }
        if request.memory_layers:
            body["memoryLayers"] = request.memory_layers

        with httpx.Client(timeout=self._timeout) as http:
            r = http.post(
                f"{self.base_url}/api/memory/search",
                headers=self._headers(),
                json=body,
            )
            r.raise_for_status()
            raw = r.json()

        return MemorySearchResult(
            result_count=raw.get("resultCount", 0),
            results=raw.get("results", []),
            raw_response=raw,
        )
