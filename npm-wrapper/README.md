# agience-flare-dkg-integration (npm wrapper)

Thin npm wrapper around the **Agience FLARE × DKG v10 Integration** Python package shipped on PyPI as [`agience-flare-dkg-integration`](https://pypi.org/project/agience-flare-dkg-integration/).

The wrapper exists so the integration can be installed via `npm install -g` and resolved through the [OriginTrail DKG integrations registry](https://github.com/OriginTrail/dkg-integrations) `cli`-kind install flow, without bundling Python or running any install-time scripts.

## What this package is — and is not

**Is:** a 50-line Node CLI shim that spawns the Python `agience-dkg` CLI if it is on PATH, or prints a single clear `pipx install` / `pip install` hint if it is not.

**Is not:** an alternative implementation. All logic — Working Memory writes, Shared Memory promotion, FLARE confidential retrieval, governed-mode commit-receipt projection, MCP Streamable HTTP transport, typed `agience:` RDF Knowledge Asset shaping — lives in the Python package.

## Security posture

- **No `preinstall`, `install`, or `postinstall` scripts.** Section 8a-compliant.
- **No dynamic code loading.** No `eval`, no remote module fetch.
- **No runtime dependencies.** Zero third-party packages in `dependencies`.
- **No egress at install time.** The wrapper does nothing until you invoke `agience-dkg`.

## Install

```bash
npm install -g agience-flare-dkg-integration
```

Then install the Python CLI it wraps:

```bash
pipx install agience-flare-dkg-integration==0.4.0
# or:
python -m pip install --user agience-flare-dkg-integration==0.4.0
```

If you invoke `agience-dkg` before the Python CLI is installed, the wrapper prints the install hint above and exits with code `127`.

## Usage

All flags and subcommands pass through to the Python CLI unchanged:

```bash
agience-dkg wm-write --title "session-note" --content "…"
agience-dkg promote <ual>
agience-dkg search "topic"
```

Wrapper-only flag:

```bash
agience-dkg --wrapper-version
```

## Configuration

Set on the operator's environment, not handled by the wrapper:

| Variable | Purpose |
|---|---|
| `DKG_BASE_URL` | Local DKG node base URL (default `http://localhost:8081`) |
| `DKG_TOKEN` | Bearer token for the local DKG node |
| `DKG_CONTEXT_GRAPH` | Context Graph slug to project into |
| `AGIENCE_BASE_URL` | (governed mode) Agience platform base URL |
| `AGIENCE_TOKEN` | (governed mode) Agience bearer token |

See the [parent repository README](https://github.com/Muffinman75/agience-flare-dkg-integration#readme) and [DESIGN_BRIEF.md](https://github.com/Muffinman75/agience-flare-dkg-integration/blob/main/DESIGN_BRIEF.md) for the full integration story.

## License

MIT
