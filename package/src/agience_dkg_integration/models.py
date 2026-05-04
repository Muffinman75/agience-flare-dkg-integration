from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class MemoryTurnRequest(BaseModel):
    context_graph_id: str = Field(alias="contextGraphId")
    markdown: str
    layer: Literal["wm", "swm"] = "wm"
    session_uri: Optional[str] = Field(default=None, alias="sessionUri")
    sub_graph_name: Optional[str] = Field(default=None, alias="subGraphName")

    model_config = ConfigDict(populate_by_name=True)


class MemoryTurnResult(BaseModel):
    turn_uri: Optional[str] = Field(default=None, alias="turnUri")
    layer: Optional[str] = None
    context_graph_id: Optional[str] = Field(default=None, alias="contextGraphId")
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
