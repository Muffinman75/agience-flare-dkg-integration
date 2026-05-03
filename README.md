# Agience FLARE DKG Integration

This directory is the contributor-owned external integration package scaffold for the OriginTrail DKG v10 Round 1 submission.

## Why this lives in [`integration/`](.)

This placement is the most logical trade-off between the bounty rules and Agience exposure:

- it keeps the integration as a standalone submission artifact rather than burying it inside core platform internals
- it still lives in the Agience workspace, so the submission visibly showcases Agience and the FLARE-aligned architecture
- it can be split into its own repository or published package without needing to restructure core backend code later

## Round 1 scope

This integration targets:
- DKG v10 Working Memory as the first write surface
- Shared Memory as the next promotion path
- forward-compatibility with Verified Memory and context oracles

It does **not** treat Verified Memory as the primary submission surface.

## Public interface discipline

Per the bounty requirements, the integration should consume DKG only through supported public interfaces:
- node HTTP API
- `dkg` CLI
- MCP server

No internal DKG package imports or node patching should be introduced.

## Planned package contents

- [`integration/package/`](package) standalone package code
- [`integration/docs/`](docs) demo, security notes, maintainer statement, and submission brief assets
- [`integration/registry/`](registry) PR-ready registry payload draft for [`OriginTrail/dkg-integrations`](https://github.com/OriginTrail/dkg-integrations)

## Current status

This is a scaffold package boundary. The internal Agience backend work in [`agience-core/backend/api/dkg_integration.py`](../agience-core/backend/api/dkg_integration.py) and [`agience-core/backend/services/dkg_integration_service.py`](../agience-core/backend/services/dkg_integration_service.py) provides the first internal integration logic that this external package will wrap or expose.
