# Demo Script

## Goal

Produce a working walkthrough for the Round 1 submission showing:
- artifact creation in Agience
- approval or commit boundary
- DKG Working Memory write path
- Shared Memory promotion path or clearly demonstrated next-step path
- provenance visibility

## Suggested demo flow

### Scene 1: create knowledge in Agience

1. open the Agience workspace UI
2. create or ingest a research note, decision artifact, or structured summary
3. show that the artifact exists first as workspace-local draft knowledge

### Scene 2: review and commit

1. open the commit or review flow
2. show that durable publication in Agience requires explicit human action
3. if available, show commit-related provenance or receipt output

### Scene 3: DKG Working Memory write

1. trigger the integration path that exports the approved artifact or derived claim view
2. show the public-interface call path used by the integration package
3. show the resulting Working Memory write outcome

### Scene 4: Shared Memory progression

1. either demonstrate actual Shared Memory progression
2. or show the policy and promotion path that makes the WM artifact eligible for SWM
3. explain that Verified Memory is intentionally not the primary Round 1 focus

### Scene 5: provenance and readiness for later rounds

1. show receipt or provenance objects linking source artifact, approval, and WM write
2. explain how the same path is designed to support later VM and oracle-readiness without redesign

## Recording checklist

- [ ] screen capture is readable
- [ ] narration explains Working Memory and Shared Memory explicitly
- [ ] no hidden manual steps are omitted
- [ ] any local services or endpoints used are listed at the end of the video
- [ ] the demo reflects actual implemented behavior, not only future plans

## Repro notes to capture alongside demo

- Agience backend start command
- integration package start command or invocation path
- DKG local node start steps
- exact trigger used to write into WM
- exact trigger used to demonstrate SWM progression or SWM readiness
