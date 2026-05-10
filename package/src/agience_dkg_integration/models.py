from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class MemoryTurnRequest(BaseModel):
    context_graph_id: str = Field(alias="contextGraphId")
    markdown: str
    layer: Literal["wm", "swm"] = "wm"
    session_uri: Optional[str] = Field(default=None, alias="sessionUri")
    sub_graph_name: Optional[str] = Field(default=None, alias="subGraphName")
    artifact_type: Optional[str] = Field(default=None, alias="artifactType")
    artifact_id: Optional[str] = Field(default=None, alias="artifactId")
    title: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    collection_id: Optional[str] = Field(default=None, alias="collectionId")
    commit_receipt_id: Optional[str] = Field(
        default=None,
        alias="commitReceiptId",
        description=(
            "Agience CommitReceipt ID for the originating commit. Set automatically "
            "when the artifact is fetched via --from-agience-artifact (governed mode). "
            "When present, it is projected as agience:commitReceiptId in the JSON-LD."
        ),
    )

    model_config = ConfigDict(populate_by_name=True)


class MemoryTurnResult(BaseModel):
    turn_uri: Optional[str] = Field(default=None, alias="turnUri")
    layer: Optional[str] = None
    context_graph_id: Optional[str] = Field(default=None, alias="contextGraphId")
    status: Optional[str] = Field(default=None, description="'anchored' if UAL received, 'pending' if MCP succeeded but blockchain anchoring is pending/failed")
    error: Optional[str] = Field(default=None, description="Descriptive error if MCP succeeded but DKG anchoring failed")
    raw_response: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class AssertionPromoteRequest(BaseModel):
    name: str
    context_graph_id: str = Field(alias="contextGraphId")
    entities: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class AssertionPromoteResult(BaseModel):
    ok: bool
    name: str
    raw_response: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class MemorySearchRequest(BaseModel):
    context_graph_id: str = Field(alias="contextGraphId")
    query: str
    limit: int = 20
    memory_layers: Optional[List[str]] = Field(default=None, alias="memoryLayers")

    model_config = ConfigDict(populate_by_name=True)


class MemorySearchResult(BaseModel):
    result_count: int = Field(default=0, alias="resultCount")
    results: List[Dict[str, Any]] = Field(default_factory=list)
    raw_response: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)
