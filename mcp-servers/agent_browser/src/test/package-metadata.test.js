/**
 * package.json metadata agrees with what the lock file actually installs.
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const root = path.join(__dirname, '..', '..');
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
const lock = JSON.parse(fs.readFileSync(path.join(root, 'package-lock.json'), 'utf8'));

function minimumMajor(range) {
  const match = /^>=\s*(\d+)(?:\.\d+){0,2}$/.exec(String(range).trim());
  assert.ok(match, `engines range must be a simple ">=N" lower bound, got ${range}`);
  return Number(match[1]);
}

test('engines.node is at least what every locked dependency requires', () => {
  const declared = minimumMajor(pkg.engines.node);
  for (const [name, entry] of Object.entries(lock.packages)) {
    if (!name || !entry.engines || !entry.engines.node) continue;
    const required = /^>=\s*(\d+)/.exec(entry.engines.node);
    if (!required) continue;
    assert.ok(declared >= Number(required[1]), `${name} needs node ${entry.engines.node}, package.json says ${pkg.engines.node}`);
  }
});

test('the running node satisfies engines.node', () => {
  assert.ok(Number(process.versions.node.split('.')[0]) >= minimumMajor(pkg.engines.node));
});
