#!/usr/bin/env bash
# Exercise the real Codex marketplace and install commands without user settings.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
export CODEX_HOME="$work/codex"
mkdir -p "$CODEX_HOME"

codex plugin marketplace add "$root" --json > "$work/marketplace.json"
for plugin in axiomatic-design-skills adhcl; do
  codex plugin add "$plugin@axiomatic-design-marketplace" --json > "$work/$plugin.json"
done
codex plugin list --marketplace axiomatic-design-marketplace --json > "$work/installed.json"

node - "$root" "$work" <<'JS'
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const [root, work] = process.argv.slice(2);
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const installed = read(path.join(work, 'installed.json')).installed;
assert.equal(installed.length, 2);
for (const [name, skill] of [
  ['axiomatic-design-skills', 'axiomatic-software-design'],
  ['adhcl', 'adhcl'],
  ['adhcl', 'adhcl-scaffold'],
]) {
  assert(installed.some(plugin => plugin.name === name && plugin.enabled));
  const result = read(path.join(work, name + '.json'));
  const source = path.join(root, 'plugins', name);
  const manifest = read(path.join(result.installedPath, 'plugin.json'));
  const claude = read(path.join(source, '.claude-plugin/plugin.json'));
  assert.equal(manifest.name, claude.name);
  assert.equal(manifest.version, claude.version);
  // Explicitly prevent fallback to the Claude Code hooks/hooks.json.
  assert.deepEqual(manifest.extensions['com.openai'].hooks, []);
  const skillDir = path.join(source, 'skills', skill);
  const bundled = ['references', 'scripts']
    .filter(dir => fs.existsSync(path.join(skillDir, dir)))
    .flatMap(dir => fs.readdirSync(path.join(skillDir, dir)).map(file => dir + '/' + file));
  for (const relative of ['SKILL.md', ...bundled]) {
    const relativePath = path.join('skills', skill, relative);
    assert.deepEqual(fs.readFileSync(path.join(result.installedPath, relativePath)), fs.readFileSync(path.join(source, relativePath)));
  }
}
console.log('Codex installed both plugins with their skills, references, and scripts.');
JS
