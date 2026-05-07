from __future__ import annotations

import os

import typer

from .client import DkgHttpClient
from .formatter import artifact_to_markdown, session_uri_for_collection
from .models import AssertionPromoteRequest, MemorySearchRequest, MemoryTurnRequest

app = typer.Typer(
    help=(
        "agience-dkg — Agience to DKG v10 Working Memory and Shared Memory CLI.\n\n"
        "Credentials are read from DKG_BASE_URL and DKG_TOKEN environment variables "
        "or passed explicitly via --base-url / --token."
    )
)


def _client(base_url: str | None, token: str | None) -> DkgHttpClient:
    url = base_url or os.environ.get("DKG_BASE_URL", "http://localhost:8081")
    tok = token or os.environ.get("DKG_TOKEN", "")
    if not tok:
        typer.echo("Error: DKG bearer token required. Set DKG_TOKEN or pass --token.", err=True)
        raise typer.Exit(1)
    return DkgHttpClient(base_url=url, bearer_token=tok)


@app.command("wm-write")
def wm_write(
    title: str = typer.Option(..., help="Artifact title"),
    artifact_type: str = typer.Option(..., help="Artifact type (e.g. research-note, decision, claim)"),
    artifact_id: str = typer.Option(..., help="Stable artifact identifier"),
    content: str = typer.Option(..., help="Artifact body text"),
    context_graph_id: str = typer.Option(..., help="DKG Context Graph ID"),
    collection_id: str = typer.Option("", help="Agience collection ID (used for sessionUri grouping)"),
    author: str = typer.Option("", help="Author display name"),
    tags: str = typer.Option("", help="Comma-separated tags"),
    layer: str = typer.Option("wm", help="Memory layer: wm (Working Memory) or swm (Shared Memory)"),
    base_url: str = typer.Option("", help="DKG node base URL (overrides DKG_BASE_URL)"),
    token: str = typer.Option("", help="DKG bearer token (overrides DKG_TOKEN)"),
) -> None:
    """Write an Agience artifact as a Knowledge Asset to DKG v10 Working Memory."""
    client = _client(base_url or None, token or None)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    markdown = artifact_to_markdown(
        title=title,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        content=content,
        author=author or None,
        tags=tag_list,
        collection_id=collection_id or None,
    )
    session_uri = session_uri_for_collection(collection_id) if collection_id else None
    request = MemoryTurnRequest(
        contextGraphId=context_graph_id,
        markdown=markdown,
        layer=layer,  # type: ignore[arg-type]
        sessionUri=session_uri,
        artifactType=artifact_type,
        artifactId=artifact_id,
        title=title,
        author=author or None,
        tags=tag_list or None,
        collectionId=collection_id or None,
    )
    result = client.memory_turn(request)
    typer.echo(result.model_dump_json(indent=2))


@app.command("promote")
def promote(
    turn_uri: str = typer.Argument(..., help="turnUri returned by wm-write (e.g. agience://wm/turn/abc123)"),
    context_graph_id: str = typer.Option(..., help="DKG Context Graph ID"),
    base_url: str = typer.Option("", help="DKG node base URL (overrides DKG_BASE_URL)"),
    token: str = typer.Option("", help="DKG bearer token (overrides DKG_TOKEN)"),
) -> None:
    """Promote a Working Memory Knowledge Asset to Shared Memory (SHARE operation)."""
    client = _client(base_url or None, token or None)
    name = turn_uri.split("/")[-1]
    request = AssertionPromoteRequest(
        name=name,
        contextGraphId=context_graph_id,
    )
    result = client.assertion_promote(request)
    typer.echo(result.model_dump_json(indent=2))


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Natural language search query"),
    context_graph_id: str = typer.Option(..., help="DKG Context Graph ID"),
    limit: int = typer.Option(20, help="Maximum number of results"),
    layers: str = typer.Option("", help="Comma-separated memory layers to search (e.g. wm,swm)"),
    base_url: str = typer.Option("", help="DKG node base URL (overrides DKG_BASE_URL)"),
    token: str = typer.Option("", help="DKG bearer token (overrides DKG_TOKEN)"),
) -> None:
    """Search Working Memory and/or Shared Memory for artifacts."""
    client = _client(base_url or None, token or None)
    layer_list = [l.strip() for l in layers.split(",") if l.strip()] if layers else None
    request = MemorySearchRequest(
        contextGraphId=context_graph_id,
        query=query,
        limit=limit,
        memoryLayers=layer_list,
    )
    result = client.memory_search(request)
    typer.echo(result.model_dump_json(indent=2))
