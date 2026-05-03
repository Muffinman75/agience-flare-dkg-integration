from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkingMemoryWriteRequest(BaseModel):
    artifact_id: str
    artifact_type: str
    title: str
    content: str
    context_graph_id: str
    source_collection_id: str
    source_receipt_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class WorkingMemoryWriteResult(BaseModel):
    ok: bool
    request_target: str
    context_graph_id: str
    assertion_id: Optional[str] = None
    batch_id: Optional[str] = None
    raw_response: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")
