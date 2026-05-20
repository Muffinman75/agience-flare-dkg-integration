// Programmatic surface for the agience-flare-dkg-integration npm wrapper.
//
// The integration's library API (DkgHttpClient, AgienceClient, models) lives
// in the Python package on PyPI (`agience-flare-dkg-integration`). This npm
// package exists to make the integration installable via `npm install -g` and
// resolvable through the DKG integrations registry's `cli`-kind install flow.
//
// Node-side consumers should drive the CLI via spawn(), or call the local DKG
// node's MCP Streamable HTTP transport directly. See the repository README for
// MCP tool names and JSON-RPC shapes.
//
// SPDX-License-Identifier: MIT

import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const pkg = require('./package.json');

export const wrapperVersion = pkg.version;
export const pythonPackage = 'agience-flare-dkg-integration';
export const pythonCli = 'agience-dkg';

export default {
  wrapperVersion,
  pythonPackage,
  pythonCli,
};
