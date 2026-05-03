from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from .models import WorkingMemoryWriteRequest, WorkingMemoryWriteResult


class DkgHttpClient:
    def __init__(self, base_url: str, bearer_token: str, *, timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }

    def write_working_memory(self, request: WorkingMemoryWriteRequest) -> WorkingMemoryWriteResult:
        payload: Dict[str, Any] = {
            "contextGraphId": request.context_graph_id,
            "title": request.title,
            "content": request.content,
            "metadata": {
                "artifactId": request.artifact_id,
                "artifactType": request.artifact_type,
                "sourceCollectionId": request.source_collection_id,
                "sourceReceiptIds": request.source_receipt_ids,
                "tags": request.tags,
                **request.metadata,
            },
        }
        endpoint = f"{self.base_url}/v1/working-memory/write"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(endpoint, headers=self._headers(), json=payload)
            response.raise_for_status()
            body = response.json()
        return WorkingMemoryWriteResult(
            ok=True,
            request_target=endpoint,
            context_graph_id=request.context_graph_id,
            assertion_id=body.get("assertionId") or body.get("id"),
            batch_id=body.get("batchId"),
            raw_response=body,
        )


def write_working_memory_via_http(
    *,
    base_url: str,
    bearer_token: str,
    request: WorkingMemoryWriteRequest,
    timeout: float = 20.0,
) -> WorkingMemoryWriteResult:
    client = DkgHttpClient(base_url=base_url, bearer_token=bearer_token, timeout=timeout)
    return client.write_working_memory(request)
