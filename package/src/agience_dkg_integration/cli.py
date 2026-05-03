from __future__ import annotations

import json
from pathlib import Path

import typer

from .client import write_working_memory_via_http
from .models import WorkingMemoryWriteRequest

app = typer.Typer(help="Agience FLARE DKG integration CLI")


@app.command("wm-write")
def wm_write(
    request_file: Path = typer.Argument(..., exists=True, readable=True, help="Path to JSON request payload"),
    base_url: str = typer.Option(..., help="Base URL for the DKG node HTTP API"),
    bearer_token: str = typer.Option(..., help="Bearer token for the DKG node"),
) -> None:
    payload = json.loads(request_file.read_text(encoding="utf-8"))
    request = WorkingMemoryWriteRequest(**payload)
    result = write_working_memory_via_http(
        base_url=base_url,
        bearer_token=bearer_token,
        request=request,
    )
    typer.echo(result.model_dump_json(indent=2))
