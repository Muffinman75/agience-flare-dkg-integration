"""Convert Agience artifacts to structured Markdown for DKG v10 Knowledge Assets.

The DKG node ingests Markdown and extracts RDF triples from structured field
headers.  Consistent field names produce consistent, queryable triples across
all artifacts written by this integration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def artifact_to_markdown(
    *,
    title: str,
    artifact_type: str,
    artifact_id: str,
    content: str,
    author: Optional[str] = None,
    tags: Optional[List[str]] = None,
    source_url: Optional[str] = None,
    committed_at: Optional[str] = None,
    collection_id: Optional[str] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> str:
    """Return structured Markdown representing one Agience artifact as a DKG Knowledge Asset.

    Field headers follow the same pattern as github-dkg and Agience autoresearch
    artifacts so that the DKG node can extract consistent RDF predicates.
    """
    now = committed_at or datetime.now(timezone.utc).isoformat()
    tag_str = ", ".join(tags) if tags else ""

    lines: List[str] = [
        f"**Agience Artifact:** {title}",
        f"**Type:** {artifact_type}  |  **ID:** {artifact_id}",
    ]
    if author:
        lines.append(f"**Author:** {author}")
    if collection_id:
        lines.append(f"**Collection:** {collection_id}")
    if tag_str:
        lines.append(f"**Tags:** {tag_str}")
    lines.append(f"**Committed:** {now}")
    if source_url:
        lines.append(f"**Source:** {source_url}")

    if extra_fields:
        for key, value in extra_fields.items():
            lines.append(f"**{key}:** {value}")

    lines.append("")
    lines.append("**Content:**")
    lines.append(content)

    return "\n".join(lines)


def session_uri_for_collection(collection_id: str, base_uri: str = "agience://collections") -> str:
    """Return a stable sessionUri that scopes all Knowledge Assets for one Agience collection.

    This allows a context oracle to retrieve all assets for a collection in a
    single query, matching the same pattern used by github-dkg for repositories.
    """
    return f"{base_uri}/{collection_id}"
