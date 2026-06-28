from __future__ import annotations

import json
import os
from importlib.metadata import version as get_package_version

import typer

from ._env import load_env

load_env()

from .agience_client import (
    AgienceClient,
    AgienceClientError,
    ArtifactNotCommittedError,
)
from .client import DkgHttpClient
from .daemon_client import DkgDaemonClient
from .formatter import artifact_to_markdown, session_uri_for_collection
from .models import AssertionPromoteRequest, MemorySearchRequest, MemoryTurnRequest

DkgClient = DkgHttpClient | DkgDaemonClient

def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"agience-dkg {get_package_version('agience-flare-dkg-integration')}")
        raise typer.Exit()


app = typer.Typer(
    help=(
        "agience-dkg \u2014 the governance layer above the OriginTrail DKG v10 daemon.\n\n"
        "Bridges committed Agience artifacts into DKG Working Memory and Shared Memory "
        "as typed `agience:` RDF Knowledge Assets, with policy-aware projection and "
        "provenance receipts. Speaks two supported v10 public interfaces \u2014 the "
        "local daemon HTTP API (default, canonical) and MCP Streamable HTTP "
        "(for nodes fronted by `dkg mcp setup`).\n\n"
        "Defaults: --transport=daemon, --base-url=http://127.0.0.1:9201, "
        "daemon bearer token auto-read from ~/.dkg/auth.token. "
        "Override any of these with flags, DKG_TRANSPORT, DKG_BASE_URL, or DKG_DAEMON_TOKEN."
    )
)


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    pass


def _ka_name_from_ref(ref: str) -> str:
    """Resolve a Knowledge Asset *name* from a CLI argument.

    DKG v10.0.1 keys SHARE/PUBLISH by the KA ``name`` returned by ``wm-write``
    (e.g. ``<artifactId>-<title-slug>``), **not** by the ``turnUri``. The v10.0.1
    WM/SWM/VM ``turnUri`` ends in a numeric revision index
    (``\u2026/_working_memory/{addr}/{n}``) that does not contain the name, so it
    cannot be split back into one. Accept the KA name directly while still
    tolerating a legacy ``\u2026/assertion/{addr}/{name}`` URI (whose final path
    segment *is* the name).
    """
    if any(
        marker in ref
        for marker in ("/_working_memory/", "/_shared_memory/", "/_verifiable_memory/")
    ):
        raise typer.BadParameter(
            "Pass the Knowledge Asset name from wm-write output "
            "(e.g. '<artifactId>-<title-slug>'), not the v10.0.1 turnUri \u2014 the "
            "turnUri ends in a revision index and does not contain the KA name."
        )
    return ref.split("/")[-1]


def _client(
    base_url: str | None,
    token: str | None,
    transport: str | None = None,
) -> DkgClient:
    """Build a transport-appropriate DKG client.

    Two transports are supported (both are stable DKG v10 public interfaces
    per bounty § 5):

    * ``daemon`` **(default)**: talks directly to the official OriginTrail
      DKG v10 daemon's HTTP API (``http://127.0.0.1:9201`` by default).
      Reads the bearer token from explicit ``--token`` →
      ``DKG_DAEMON_TOKEN`` → ``~/.dkg/auth.token`` → ``DKG_TOKEN``.
      WM writes do not require an on-chain publish; the daemon stores
      assertions locally until ``share`` is called.
    * ``mcp``: talks to a DKG node's ``POST /mcp`` endpoint via MCP
      Streamable HTTP. Used for MCP-fronted nodes (e.g. those configured
      via ``dkg mcp setup``). Requires DKG_TOKEN.
    """
    chosen = (transport or os.environ.get("DKG_TRANSPORT") or "daemon").lower()
    url = base_url or os.environ.get("DKG_BASE_URL")

    if chosen == "daemon":
        # The daemon transport never accepts DKG_TOKEN as a fallback inside
        # this helper because deployments commonly pin DKG_TOKEN to an MCP-
        # flavour token that the local daemon will reject. DkgDaemonClient
        # itself walks DKG_DAEMON_TOKEN -> ~/.dkg/auth.token -> DKG_TOKEN.
        return DkgDaemonClient(
            base_url=url or "http://127.0.0.1:9201",
            bearer_token=token or None,
        )

    tok = token or os.environ.get("DKG_TOKEN", "")
    if not tok:
        typer.echo(
            "Error: DKG bearer token required for MCP transport. "
            "Set DKG_TOKEN, pass --token, or switch to --transport daemon.",
            err=True,
        )
        raise typer.Exit(1)
    return DkgHttpClient(base_url=url or "http://localhost:8083", bearer_token=tok)


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
    transport: str = typer.Option(
        "",
        "--transport",
        help=(
            "DKG transport: 'daemon' (default \u2014 direct HTTP to a local "
            "OriginTrail DKG v10 daemon) or 'mcp' (via the /mcp endpoint, "
            "for nodes fronted by `dkg mcp setup`). Override via DKG_TRANSPORT."
        ),
    ),
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
    ag: AgienceClient | None = None

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

    chosen_transport = (transport or os.environ.get("DKG_TRANSPORT") or "daemon").lower()
    resolved_base_url = base_url or os.environ.get("DKG_BASE_URL") or (
        "http://127.0.0.1:9201" if chosen_transport == "daemon" else "http://localhost:8083"
    )
    resolved_agience_url = agience_base_url or os.environ.get("AGIENCE_BASE_URL") or "http://localhost:8081"
    _token_display = (token or "")[:8] + "..." if (token or "") else "(env/file)"
    _agience_token_display = (agience_token or "")[:8] + "..." if (agience_token or "") else "(env)"
    typer.echo(
        "# agience-dkg wm-write — resolved invocation (copy to replay):\n"
        f"agience-dkg wm-write \\\n"
        f"  --transport {chosen_transport} \\\n"
        f"  --from-agience-artifact \"{from_agience_artifact}\" \\\n"
        f"  --title \"{title}\" \\\n"
        f"  --artifact-type \"{artifact_type}\" \\\n"
        f"  --context-graph-id \"{context_graph_id}\" \\\n"
        f"  --base-url \"{resolved_base_url}\" \\\n"
        f"  --token \"{_token_display}\" \\\n"
        f"  --agience-base-url \"{resolved_agience_url}\" \\\n"
        f"  --agience-token \"{_agience_token_display}\""
    )

    client = _client(base_url or None, token or None, transport or None)
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

    # Best-effort provenance write-back: record the real UAL/stage on the
    # Agience artifact so its DKG Projection panel reflects the live node.
    # Only in governed mode (we have an artifact id) and only when anchored.
    if from_agience_artifact and ag is not None and result.status == "anchored":
        chosen_transport = (transport or os.environ.get("DKG_TRANSPORT") or "daemon").lower()
        stage = "swm" if layer == "swm" else "wm"
        publish_state = "promoted" if layer == "swm" else "written"
        try:
            ag.record_publication(
                from_agience_artifact,
                dkg_stage=stage,
                context_graph_id=context_graph_id,
                publish_state=publish_state,
                ual=result.turn_uri,
                turn_uri=result.turn_uri,
                transport=chosen_transport,
            )
        except AgienceClientError as exc:
            typer.echo(
                f"Note: DKG write succeeded but recording it back to Agience "
                f"failed (panel will fall back to the projection plan): {exc}",
                err=True,
            )


def _share(
    turn_uri: str,
    context_graph_id: str,
    base_url: str | None,
    token: str | None,
    transport: str | None,
    from_agience_artifact: str | None,
    agience_base_url: str | None,
    agience_token: str | None,
    command_name: str = "share",
) -> None:
    """Shared implementation for share / promote (Curator-authorized SHARE to SWM)."""
    client = _client(base_url, token, transport)
    name = _ka_name_from_ref(turn_uri)
    request = AssertionPromoteRequest(
        name=name,
        contextGraphId=context_graph_id,
    )
    result = client.assertion_promote(request)
    typer.echo(result.model_dump_json(indent=2))

    # Best-effort provenance write-back of the Shared Memory promotion.
    if from_agience_artifact and result.ok:
        chosen_transport = (transport or os.environ.get("DKG_TRANSPORT") or "daemon").lower()
        try:
            ag = AgienceClient(
                base_url=agience_base_url or None,
                bearer_token=agience_token or None,
            )
            ag.record_publication(
                from_agience_artifact,
                dkg_stage="swm",
                context_graph_id=context_graph_id,
                publish_state="promoted",
                ual=turn_uri,
                assertion_id=name,
                turn_uri=turn_uri,
                transport=chosen_transport,
            )
        except AgienceClientError as exc:
            typer.echo(
                f"Note: {command_name} succeeded but recording it back to Agience failed: {exc}",
                err=True,
            )


@app.command("share")
def share(
    turn_uri: str = typer.Argument(..., help="Knowledge Asset NAME from wm-write output (e.g. '<artifactId>-<title-slug>'). NOT the v10.0.1 turnUri."),
    context_graph_id: str = typer.Option(..., help="DKG Context Graph ID"),
    base_url: str = typer.Option("", help="DKG node base URL (overrides DKG_BASE_URL)"),
    token: str = typer.Option("", help="DKG bearer token (overrides DKG_TOKEN)"),
    transport: str = typer.Option("", "--transport", help="'daemon' (default) or 'mcp'. Overridable via DKG_TRANSPORT."),
    from_agience_artifact: str = typer.Option(
        "",
        "--from-agience-artifact",
        help=(
            "Agience artifact id this assertion was projected from. When set, "
            "the SWM share is recorded back to Agience so its DKG Projection "
            "panel shows the Shared Memory stage. Best-effort; never blocks share."
        ),
    ),
    agience_base_url: str = typer.Option("", help="Agience backend URL (overrides AGIENCE_BASE_URL)"),
    agience_token: str = typer.Option("", help="Agience bearer token (overrides AGIENCE_TOKEN)"),
) -> None:
    """Share a Working Memory Knowledge Asset to Shared Memory (Curator-authorized SHARE).

    This is the v10.0.1 name for the operation historically called ``promote``.
    Explicit and operator-initiated — never automatic. Eligibility is gated upstream
    by the Agience `PolicyMappingRecord.promotion_profile` (must be `swm-eligible`
    or `vm-eligible`). Preserves the UAL chain for Round 2 Verified Memory.
    """
    _share(
        turn_uri=turn_uri,
        context_graph_id=context_graph_id,
        base_url=base_url or None,
        token=token or None,
        transport=transport or None,
        from_agience_artifact=from_agience_artifact or None,
        agience_base_url=agience_base_url or None,
        agience_token=agience_token or None,
        command_name="share",
    )


@app.command("promote")
def promote(
    turn_uri: str = typer.Argument(..., help="Knowledge Asset NAME from wm-write output (e.g. '<artifactId>-<title-slug>'). NOT the v10.0.1 turnUri."),
    context_graph_id: str = typer.Option(..., help="DKG Context Graph ID"),
    base_url: str = typer.Option("", help="DKG node base URL (overrides DKG_BASE_URL)"),
    token: str = typer.Option("", help="DKG bearer token (overrides DKG_TOKEN)"),
    transport: str = typer.Option("", "--transport", help="'daemon' (default) or 'mcp'. Overridable via DKG_TRANSPORT."),
    from_agience_artifact: str = typer.Option(
        "",
        "--from-agience-artifact",
        help=(
            "Agience artifact id this assertion was projected from. When set, "
            "the SWM share is recorded back to Agience so its DKG Projection "
            "panel shows the Shared Memory stage. Best-effort; never blocks share."
        ),
    ),
    agience_base_url: str = typer.Option("", help="Agience backend URL (overrides AGIENCE_BASE_URL)"),
    agience_token: str = typer.Option("", help="Agience bearer token (overrides AGIENCE_TOKEN)"),
) -> None:
    """Backward-compatible alias for ``share`` (historically called promote).

    Shares a Working Memory Knowledge Asset to Shared Memory (Curator-authorized SHARE).
    """
    _share(
        turn_uri=turn_uri,
        context_graph_id=context_graph_id,
        base_url=base_url or None,
        token=token or None,
        transport=transport or None,
        from_agience_artifact=from_agience_artifact or None,
        agience_base_url=agience_base_url or None,
        agience_token=agience_token or None,
        command_name="promote",
    )


@app.command("vm-publish")
def vm_publish(
    turn_uri: str = typer.Argument(..., help="Knowledge Asset NAME from wm-write output (e.g. '<artifactId>-<title-slug>'). NOT the v10.0.1 turnUri."),
    context_graph_id: str = typer.Option(..., help="DKG Context Graph ID (must be on-chain registered)"),
    sub_graph_name: str = typer.Option("", "--sub-graph-name", help="Optional named sub-graph to publish"),
    publish_epochs: int = typer.Option(0, "--publish-epochs", help="Number of epochs to keep the asset published (0 = daemon default)"),
    base_url: str = typer.Option("", help="DKG node base URL (overrides DKG_BASE_URL)"),
    token: str = typer.Option("", help="DKG bearer token (overrides DKG_TOKEN)"),
    transport: str = typer.Option("", "--transport", help="Must be 'daemon' (VM publish is daemon-only). Overridable via DKG_TRANSPORT."),
    from_agience_artifact: str = typer.Option(
        "",
        "--from-agience-artifact",
        help=(
            "Agience artifact id this assertion was projected from. When set, a "
            "successful on-chain publish is recorded back to Agience so its DKG "
            "Projection panel shows the Verifiable Memory stage. Best-effort."
        ),
    ),
    agience_base_url: str = typer.Option("", help="Agience backend URL (overrides AGIENCE_BASE_URL)"),
    agience_token: str = typer.Option("", help="Agience bearer token (overrides AGIENCE_TOKEN)"),
) -> None:
    """Publish a shared Knowledge Asset to Verifiable Memory (on-chain, DKG v10.0.1+).

    Mints (or updates) the Knowledge Asset on chain via the daemon's
    ``/api/knowledge-assets/{name}/vm/publish`` route. The assertion must already
    be finalized and shared to SWM (run `share` first), the Context Graph must
    be on-chain registered, and the node needs gas + TRAC and a reliable RPC.

    Daemon-only: VM publish has no MCP equivalent. Best-effort — a failed publish
    reports the daemon's error rather than crashing, so the WM/SWM provenance is
    preserved.
    """
    client = _client(base_url or None, token or None, transport or None)
    if not isinstance(client, DkgDaemonClient):
        typer.echo(
            "Error: vm-publish is only supported on the daemon transport "
            "(--transport daemon). MCP-fronted nodes do not expose VM publish.",
            err=True,
        )
        raise typer.Exit(1)

    name = _ka_name_from_ref(turn_uri)
    result = client.vm_publish(
        name=name,
        context_graph_id=context_graph_id,
        sub_graph_name=sub_graph_name or None,
        publish_epochs=publish_epochs or None,
    )
    typer.echo(json.dumps(result, indent=2))

    if not result.get("ok"):
        # Surface a non-zero exit so scripts can detect an unconfirmed publish,
        # but the receipt has already been printed for diagnosis.
        raise typer.Exit(4)

    # Best-effort provenance write-back of the Verifiable Memory publish.
    if from_agience_artifact:
        chosen_transport = (transport or os.environ.get("DKG_TRANSPORT") or "daemon").lower()
        try:
            ag = AgienceClient(
                base_url=agience_base_url or None,
                bearer_token=agience_token or None,
            )
            ag.record_publication(
                from_agience_artifact,
                dkg_stage="vm",
                context_graph_id=context_graph_id,
                publish_state="published",
                ual=result.get("ual") or turn_uri,
                assertion_id=name,
                turn_uri=turn_uri,
                transport=chosen_transport,
            )
        except AgienceClientError as exc:
            typer.echo(
                f"Note: VM publish succeeded but recording it back to Agience failed: {exc}",
                err=True,
            )


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Natural language search query"),
    context_graph_id: str = typer.Option(..., help="DKG Context Graph ID"),
    limit: int = typer.Option(20, help="Maximum number of results"),
    layers: str = typer.Option("", help="Comma-separated memory layers to search (e.g. wm,swm)"),
    base_url: str = typer.Option("", help="DKG node base URL (overrides DKG_BASE_URL)"),
    token: str = typer.Option("", help="DKG bearer token (overrides DKG_TOKEN)"),
    transport: str = typer.Option("", "--transport", help="'daemon' (default) or 'mcp'. Overridable via DKG_TRANSPORT."),
) -> None:
    """Search Working / Shared Memory via SPARQL using `agience:` predicates.

    Filterable by memory layer, artifact type, author, collection, and sessionUri.
    Read-only. Scoped to the supplied Context Graph.
    """
    client = _client(base_url or None, token or None, transport or None)
    layer_list = [l.strip() for l in layers.split(",") if l.strip()] if layers else None
    request = MemorySearchRequest(
        contextGraphId=context_graph_id,
        query=query,
        limit=limit,
        memoryLayers=layer_list,
    )
    result = client.memory_search(request)
    typer.echo(result.model_dump_json(indent=2))
