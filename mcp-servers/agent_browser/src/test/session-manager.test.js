const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

test('session identifiers cannot escape the profile root', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ae-browser-boundary-'));
  try {
    const { SessionManager } = require('../session-manager.js');
    const manager = new SessionManager({ profileRoot: root });
    for (const value of ['../outside', '..', '.', '/absolute', 'nested/session', 'nested\\session']) {
      assert.throws(() => manager.getProfilePath(value), /invalid session/i);
    }
    assert.equal(manager.getProfilePath('sess-fixture_1'), path.join(root, 'sess-fixture_1'));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('browser profiles and session indexes stay in the active checkout', () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'ae-browser-state-'));
  try {
    const checkout = path.join(temporary, 'checkout');
    const source = path.join(checkout, 'mcp-servers', 'agent_browser', 'src', 'session-manager.js');
    fs.mkdirSync(path.dirname(source), { recursive: true });
    fs.copyFileSync(path.join(__dirname, '..', 'session-manager.js'), source);
    const home = path.join(temporary, 'external-home');
    fs.mkdirSync(home);
    const script = `
      const assert = require('node:assert/strict');
      const fs = require('node:fs');
      const path = require('node:path');
      const {SessionManager, DEFAULT_PROFILE_ROOT} = require(process.argv[1]);
      const checkout = process.argv[2];
      assert.ok(DEFAULT_PROFILE_ROOT.startsWith(checkout + path.sep));
      (async () => {
        const profileRoot = path.join(checkout, '.agentenhancements', 'cache', 'custom-browser');
        const manager = new SessionManager({profileRoot});
        await manager.createSession({sessionId: 'fixture-session'});
        const saved = new SessionManager({profileRoot});
        assert.ok(saved.getSessionMetadata('fixture-session'));
        const other = new SessionManager({profileRoot: profileRoot + '-other'});
        assert.equal(other.getSessionMetadata('fixture-session'), null);
        assert.equal(fs.statSync(profileRoot).mode & 0o777, 0o700);
        assert.equal(fs.statSync(path.join(profileRoot, 'sessions.json')).mode & 0o777, 0o600);
      })().catch(error => { console.error(error); process.exitCode = 1; });
    `;
    const env = { ...process.env, HOME: home };
    delete env.AGENT_ENHANCEMENTS_STATE_DIR;
    execFileSync(process.execPath, ['-e', script, source, checkout], { env, stdio: 'pipe' });
    assert.equal(fs.existsSync(path.join(home, '.agent-browser')), false);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});
