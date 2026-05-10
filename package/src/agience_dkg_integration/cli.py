from __future__ import annotations

import os

import typer

from .agience_client import (
    AgienceClient,
    AgienceClientError,
    ArtifactNotCommittedError,
)
from .client import DkgHttpClient
from .formatter import artifact_to_markdown, session_uri_for_collection
from .models import AssertionPromoteRequest, MemorySearchRequest, MemoryTurnRequest

app = typer.Typer(
    help=(
        "agience-dkg \u2014 the governance layer above DKG v10's MCP transport.\n\n"
        "Bridges committed Agience artifacts into DKG Working Memory and Shared Memory "
        "as typed `agience:` RDF Knowledge Assets, with policy-aware projection and "
        "provenance receipts. Where `dkg mcp setup` solves transport, this solves "
        "governance: human-review commit boundaries, typed artifact metadata, and "
        "Curator-authorized SHARE.\n\n"
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
    context_graph_id: str = typer.Option(..., help="DKG Context Graph ID"),
    from_agience_artifact: str = typer.Option(
        "",
        "--from-agience-artifact",
        help=(
            "GOVERNED MODE: fetch the named artifact from a running Agience instance "
            "(AGIENCE_BASE_URL / AGIENCE_TOKEN) and refuse to project unless its "
            "state is `committed`. Populates title/type/content/author/tags/collection "
            "from the Agience record and attaches the commit_receipt_id. "
            "When set, the explicit --title/--content/etc. options are optional and "
            "act as overrides."
        ),
    ),
    title: str = typer.Option("", help="Artifact title (required unless --from-agience-artifact)"),
    artifact_type: str = typer.Option("", help="Artifact type (e.g. research-note, decision, claim)"),
    artifact_id: str = typer.Option("", help="Stable artifact identifier"),
    content: str = typer.Option("", help="Artifact body text"),
    collection_id: str = typer.Option("", help="Agience collection ID (used for sessionUri grouping)"),
    author: str = typer.Option("", help="Author display name"),
    tags: str = typer.Option("", help="Comma-separated tags"),
    layer: str = typer.Option("wm", help="Memory layer: wm (Working Memory) or swm (Shared Memory)"),
    base_url: str = typer.Option("", help="DKG node base URL (overrides DKG_BASE_URL)"),
    token: str = typer.Option("", help="DKG bearer token (overrides DKG_TOKEN)"),
    agience_base_url: str = typer.Option("", help="Agience backend URL (overrides AGIENCE_BASE_URL)"),
    agience_token: str = typer.Option("", help="Agience bearer token (overrides AGIENCE_TOKEN)"),
) -> None:
    """Write a governed Agience artifact as a typed `agience:` Knowledge Asset.

    Records artifact metadata (type, author, collection, sessionUri, memoryLayer)
    so the resulting Knowledge Asset is SPARQL-queryable across Context Graphs.
    Returns the UAL (turn_uri) and an explicit anchored/pending status.

    Use --from-agience-artifact to enforce upstream governance: the artifact is
    fetched from a live Agience instance and rejected unless it has been
    committed (i.e. has passed the human-review boundary).
    """
    commit_receipt_id: str | None = None

    if from_agience_artifact:
        try:
            ag = AgienceClient(
                base_url=agience_base_url or None,
                bearer_token=agience_token or None,
            )
            artifact = ag.get_committed_artifact(from_agience_artifact)
        except ArtifactNotCommittedError as exc:
            typer.echo(f"Governance error: {exc}", err=True)
            raise typer.Exit(2)
        except AgienceClientError as exc:
            typer.echo(f"Agience error: {exc}", err=True)
            raise typer.Exit(3)

        title = title or artifact.title
        artifact_type = artifact_type or artifact.artifact_type
        artifact_id = artifact_id or artifact.id
        content = content or artifact.content
        author = author or (artifact.author or "")
        if not tags and artifact.tags:
            tags = ",".join(artifact.tags)
        collection_id = collection_id or (artifact.collection_id or "")
        commit_receipt_id = artifact.commit_receipt_id

    missing = [
        name
        for name, value in (
            ("--title", title),
            ("--artifact-type", artifact_type),
            ("--artifact-id", artifact_id),
            ("--content", content),
        )
        if not value
    ]
    if missing:
        hint = " (or supply --from-agience-artifact)" if not from_agience_artifact else ""
        typer.echo(f"Error: missing required option(s): {', '.join(missing)}{hint}", err=True)
        raise typer.Exit(1)

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
        commitReceiptId=commit_receipt_id,
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
    """Promote a Working Memory Knowledge Asset to Shared Memory (Curator-authorized SHARE).

    Explicit and operator-initiated — never automatic. Eligibility is gated upstream
    by the Agience `PolicyMappingRecord.promotion_profile` (must be `swm-eligible`
    or `vm-eligible`). Preserves the UAL chain for Round 2 Verified Memory.
    """
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
    """Search Working / Shared Memory via SPARQL using `agience:` predicates.

    Filterable by memory layer, artifact type, author, collection, and sessionUri.
    Read-only. Scoped to the supplied Context Graph.
    """
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
