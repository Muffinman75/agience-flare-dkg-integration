# Registry Entry Template

Use this as the draft source for the eventual PR to [`OriginTrail/dkg-integrations`](https://github.com/OriginTrail/dkg-integrations).

## Required final values

- integration slug
- repository URL
- pinned commit SHA
- published package version
- license and SPDX identifier
- declared network egress
- declared write authority
- maintainer details

## Draft submission metadata

- Name: Agience FLARE DKG Integration
- Slug: `agience-flare-dkg-integration`
- Category: agent-memory / research-workflow integration
- Round fit: DKG v10 Round 1 Working Memory and Shared Memory
- Primary interfaces: `HTTP API`
- Repository URL: to be finalized from the contributor-owned repository that will contain [`integration/package/`](../package)
- Package version: `0.1.0`
- Commit SHA: to be finalized at release cut
- License: `MIT`
- SPDX: `MIT`
- Maintainer: Agience team placeholder; replace contact before PR

## Declared network egress

- local or target DKG node HTTP endpoint
- optional Agience backend endpoint if deployed separately from the integration package
- optional FLARE service endpoint only if confidential retrieval mediation is enabled in the submission build

## Declared write authority

Current implemented target authority:
- Working Memory write via the DKG HTTP API

Not enabled by default in the current implementation and must be declared separately if later added:
- Shared Memory promotion
- PUBLISH-related publication steps toward Verified Memory

## Compliance notes

- current package scaffold is implemented under [`integration/package/`](../package)
- current DKG path uses public HTTP API and does not rely on internal DKG package imports
- no dynamic code loading is part of the current scaffold
- maintainer contact still needs final replacement before PR creation

## Suggested PR checklist

- [ ] package published with provenance
- [ ] no preinstall or postinstall scripts without explicit justification
- [x] license file and SPDX selected as `MIT` for the external package scaffold
- [x] network egress list drafted
- [x] DKG write authority list drafted
- [x] no dynamic code loading in current scaffold
- [ ] maintainer contact finalized
- [ ] demo link added
- [ ] design brief link added
