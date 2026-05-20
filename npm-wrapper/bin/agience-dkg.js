#!/usr/bin/env node
// Thin Node-side wrapper around the Python `agience-dkg` CLI shipped on PyPI as
// `agience-flare-dkg-integration`. This wrapper exists purely so the integration
// can be installed via `npm install -g` (and resolved by the DKG integrations
// registry installer) without bundling Python. It does *not* download, install,
// or execute any remote code at install time: no postinstall hooks, no eval,
// no remote fetch. All it does at runtime is spawn `agience-dkg` if it is on
// PATH, or print a single clear install hint if it is not.
//
// SPDX-License-Identifier: MIT

import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const pkg = require('../package.json');

const PYTHON_PACKAGE = 'agience-flare-dkg-integration';
const PYTHON_CLI = 'agience-dkg';
const PINNED_VERSION = pkg.version;

const args = process.argv.slice(2);

// `--wrapper-version` is a wrapper-only flag so operators can see exactly which
// npm wrapper they have without invoking the Python side. Everything else
// passes through untouched.
if (args.length === 1 && args[0] === '--wrapper-version') {
  process.stdout.write(`${pkg.name}@${pkg.version} (npm wrapper)\n`);
  process.exit(0);
}

run();

function run() {
  const child = spawn(PYTHON_CLI, args, {
    stdio: 'inherit',
    shell: process.platform === 'win32',
  });

  child.on('error', (err) => {
    if (err && err.code === 'ENOENT') {
      printMissingPythonCliHint();
      process.exit(127);
    }
    process.stderr.write(`agience-dkg: failed to launch underlying CLI: ${err.message}\n`);
    process.exit(1);
  });

  child.on('exit', (code, signal) => {
    if (signal) {
      process.exit(1);
    }
    process.exit(code ?? 0);
  });
}

function printMissingPythonCliHint() {
  const lines = [
    '',
    `agience-dkg: underlying Python CLI '${PYTHON_CLI}' was not found on PATH.`,
    '',
    `This npm package (${pkg.name}@${pkg.version}) is a thin wrapper around the`,
    `Python implementation shipped on PyPI as '${PYTHON_PACKAGE}'. The wrapper does`,
    'not auto-install Python dependencies (no postinstall hooks, by design).',
    '',
    'One-line install:',
    '',
    `  pipx install ${PYTHON_PACKAGE}==${PINNED_VERSION}`,
    '',
    'Or via pip:',
    '',
    `  python -m pip install --user ${PYTHON_PACKAGE}==${PINNED_VERSION}`,
    '',
    'Then re-run the same command. Configure the local DKG node endpoint with',
    'DKG_BASE_URL and DKG_TOKEN as documented in the README.',
    '',
  ];
  process.stderr.write(lines.join('\n'));
}
