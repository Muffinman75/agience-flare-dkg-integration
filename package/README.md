# Package Scaffold

This package directory contains the standalone integration implementation that will be submitted through the DKG integrations registry.

## Intended responsibilities

- expose the Agience-to-DKG Working Memory write path through a supported public DKG interface
- preserve policy and provenance semantics designed in [`plans/agience-flare-dkg-policy-mapping.md`](../../plans/agience-flare-dkg-policy-mapping.md) and [`plans/agience-flare-dkg-receipt-schemas.md`](../../plans/agience-flare-dkg-receipt-schemas.md)
- avoid any forbidden dependence on internal DKG node packages

## Current implemented slice

The first true DKG Working Memory write path is implemented through the HTTP interface in:
- [`integration/package/src/agience_dkg_integration/models.py`](src/agience_dkg_integration/models.py)
- [`integration/package/src/agience_dkg_integration/client.py`](src/agience_dkg_integration/client.py)
- [`integration/package/src/agience_dkg_integration/cli.py`](src/agience_dkg_integration/cli.py)
- [`integration/package/pyproject.toml`](pyproject.toml)

### Current command shape

Once installed, the package is intended to expose:
- [`agience-dkg wm-write`](src/agience_dkg_integration/cli.py)

This command reads a JSON payload and writes it to the DKG node's Working Memory HTTP surface.

## Expected next artifacts

- local integration test harness for the external package
- sample request fixture for demoability
- optional MCP-facing entrypoint if that becomes the preferred submission surface
