# Security Notes

## Scope

These notes are prepared for the OriginTrail DKG v10 Round 1 submission package for the Agience FLARE DKG integration.

## Credential model

The intended integration path uses supported public DKG interfaces only.

Planned credential surfaces:
- Agience-side authenticated user or service context
- local or target DKG node bearer token, CLI environment, or MCP configuration
- optional FLARE-side service credentials only when confidential retrieval mediation is enabled

## Declared network egress

Expected external domains or endpoints beyond local process execution:
- local or target DKG node endpoint
- optional Agience backend endpoint when the integration package is deployed separately from core
- optional FLARE service endpoint if protected retrieval is enabled

No undeclared remote code loading is part of the planned integration.

## Declared DKG write authority

Round 1 primary write authority target:
- Working Memory write path

Potential later-stage operations that must be called out explicitly if enabled:
- SHARE-related promotion into Shared Memory
- PUBLISH-related promotion toward Verified Memory

The initial package should default to the smallest required authority surface and make any escalation explicit.

## Curator authority stance

Any Curator-sensitive operation must be declared explicitly in the final registry metadata and security notes. The initial Round 1 implementation should avoid hidden SHARE or PUBLISH behavior.

## Dynamic code loading

The integration must not:
- fetch and execute remote code
- use eval on remote input
- import internal DKG node packages disallowed by the bounty rules

## Internal coupling guardrail

The external integration package should consume DKG through supported public interfaces only:
- HTTP API
- `dkg` CLI
- MCP server

It should not patch the node daemon or depend on non-public DKG package internals.

## Finalization items before submission

- replace placeholder endpoint descriptions with actual domains or local addresses used in the demo
- list exact DKG operations invoked
- confirm whether FLARE endpoint egress is enabled in the submission build
- copy the final security summary into the PR description or linked design brief
