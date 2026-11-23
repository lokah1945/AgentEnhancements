# agent_browser

An MCP server that drives Chromium over the Chrome DevTools Protocol (CDP),
using Playwright to launch the browser. It is optional and disabled in the
default AgentEnhancements configuration.

## Requirements

- Node.js >= 20, as required by the locked Playwright 1.65.1.
- Dependencies: `npm ci --ignore-scripts` in this directory.
- A Chromium build for Playwright: `npx playwright install chromium`.
  The session's `browser` field (`chrome`, `edge`, `chromium`) is recorded as
  metadata only. The server always launches Playwright's bundled Chromium.

## Running

```sh
node src/index.js                   # stdio transport (default)
MCP_HTTP_PORT=3456 node src/index.js  # HTTP transport
```

### stdio

- Each JSON-RPC 2.0 message is one line of UTF-8 JSON, ending in `\n`
  (`\r\n` is accepted). A message may be split across writes.
- stdout carries protocol frames only. All diagnostics go to stderr.
- Requests are handled one at a time, in arrival order, so tool calls never
  interleave. A long call (for example `navigate`) delays the requests after it.
- A line that is not valid JSON gets a `-32700` error with `id: null`, and
  the lines after it are still processed.
- When stdin closes, the server answers the requests it already has, closes
  every browser it launched, and exits with code 0.

### HTTP

- `POST /mcp` takes a JSON-RPC message or a batch, with
  `Content-Type: application/json`. A request gets `200` and a JSON body.
  A message made only of notifications gets `202` and no body.
- `GET /health` returns `{"status":"ok"}`. There is no SSE stream and no
  `Mcp-Session-Id`, so `cdp_subscribe` notifications are only delivered over
  stdio.

The HTTP transport is locked down by default:

| Control | Default | Override |
| --- | --- | --- |
| Bind address | `127.0.0.1` | `MCP_HTTP_HOST` |
| Bearer token | Off on loopback. A non-loopback host refuses to start without one. | `AGENT_BROWSER_HTTP_TOKEN` |
| `Host` header | Must be `localhost`, `127.0.0.1` or `[::1]` when bound to loopback, to block DNS rebinding. Otherwise `403`. | - |
| `Origin` header | When present, must be a loopback `http(s)` origin. Otherwise `403`. | `AGENT_BROWSER_HTTP_ALLOWED_ORIGINS` (comma list) |
| Content type | Must be `application/json`. Otherwise `415`, which forces a CORS preflight. | - |
| Body size | 1 MiB. Larger bodies get `413`. | `AGENT_BROWSER_HTTP_MAX_BODY_BYTES` |

The token is compared in constant time. No CORS headers are ever sent.

## Protocol support

- `initialize` negotiates `2025-06-18`, `2025-03-26` or `2024-11-05`. It
  echoes the client's version when supported, and otherwise offers the newest.
  It advertises only the `tools` capability.
- The other supported methods are `ping`, `tools/list` and `tools/call`.
  Notifications (`notifications/initialized`, `notifications/cancelled`, and
  so on) are accepted and never answered. Cancellation is not implemented.
- Batches (JSON arrays) are accepted.
- Errors:

| Code | Meaning |
| --- | --- |
| `-32700` | Parse error |
| `-32600` | Invalid request: bad `jsonrpc`, `id` or `method`, or an oversized stdio frame (`AGENT_BROWSER_MAX_MESSAGE_BYTES`, default 64 MiB) |
| `-32601` | Unknown method |
| `-32602` | Unknown tool, missing required arguments, or wrong argument types or enum values (checked against the advertised `inputSchema`) |
| `-32603` | Internal server error |

- A tool that fails returns a normal `tools/call` result with
  `isError: true` and the error text, as MCP specifies. Successful results are
  one `text` content item that holds the tool's JSON output.
- The `resources`, `prompts`, `sampling` and `logging` features are not
  implemented.

## Tools

Session tools never launch Chromium. Every other browser tool launches the
session's browser on first use. All page tools act on the session's active
tab: the first tab, or the tab last chosen with `tab_new` (not in background)
or `tab_switch`.

| Group | Tools | Notes |
| --- | --- | --- |
| Sessions | `session_create`, `session_list`, `session_get`, `session_close`, `session_delete`, `session_snapshot`, `session_restore`, `session_cleanup` | Profiles are stored under `$AGENT_ENHANCEMENTS_STATE_DIR/cache/browser/profiles`, defaulting to `<checkout>/.agentenhancements/...`, with mode 0700. Session ids are limited to `[A-Za-z0-9_.-]`. `session_create` refuses an id that already exists. `session_delete` closes a browser this process is running, and needs `force` only for a session another process still marks active. `session_snapshot` includes live cookies and storage only while the browser is running. `session_restore` recreates metadata, not cookies or storage. |
| Navigation | `navigate`, `go_back`, `go_forward`, `reload`, `get_current_url` | `waitUntil` is `domContentLoaded` (default), `load` or `networkIdle`, matched to the new document's lifecycle events. `timeout` defaults to 30000 ms. A Chromium `errorText` such as `net::ERR_NAME_NOT_RESOLVED` fails the call. History tools use the tab's navigation history and return `success: false` at either end of it. `headers` stay set for later requests of the tab. |
| Tabs | `tab_new`, `tab_switch`, `tab_close`, `tab_list`, `tab_get` | Tab ids are stable for a tab's lifetime. Popups opened by pages are listed too. |
| Interaction | `click`, `type`, `hover`, `scroll`, `drag_drop`, `key_press` | Simulated mouse and keyboard input. `humanize: false` sends direct input events. |
| Extraction | `extract`, `get_attributes`, `get_page_content` | Selectors and XPaths are passed to the page exactly as given. `extract.script` evaluates arbitrary JavaScript. |
| Observation | `screenshot`, `pdf`, `dom_snapshot`, `get_html`, `get_text` | Screenshot `quality` applies to `jpeg` only. |
| Raw CDP | `cdp_send`, `cdp_evaluate`, `cdp_subscribe`, `cdp_unsubscribe`, `cdp_metrics` | Full CDP access to the active tab. `target: "frame"` with a `frameId` selects the tab whose main frame has that id. Child frames and workers are not addressable. |
| Captures | `cdp_network_capture`, `cdp_console_capture`, `cdp_capture_get`, `cdp_capture_stop`, `cdp_capture_list` | Captures keep at most `maxEntries` entries (network 500, console 200). Network captures include response bodies unless `includeBody: false`. Closing a session stops its captures. |
| Personas | `persona_set`, `persona_get`, `persona_list_modes`, `persona_list_templates`, `persona_get_template`, `persona_validate`, `persona_create` | These tools compute behaviour parameters and return them. Nothing is stored per session (`persona_set` returns `applied: false`). To use a persona, pass it as the `persona` argument of the interaction tools. |

## Browser security defaults

- Chromium runs with the same-origin policy, site isolation and TLS
  certificate validation enabled. No permissions (geolocation, camera,
  microphone, notifications) are pre-granted.
- `AGENT_BROWSER_INSECURE=1` (or `true`, `yes`, `on`) is an explicit opt-in.
  It adds `--disable-web-security`, `--disable-site-isolation-trials`,
  `--allow-running-insecure-content`, `--ignore-certificate-errors` and
  `--allow-insecure-localhost`, logs a warning, and uses a throwaway profile
  instead of the session's persistent one.
- Every page gets an init script and CDP emulation overrides. They change what
  pages observe, including `navigator.platform`, plugins, the user agent and
  client hints, the timezone, the hardware concurrency and the device memory.
  See `src/launch-config.js` and `src/cdp-router-wrapper.js`.
- A browser that exits on its own is removed from the server's state. The next
  browser tool call relaunches it.

## Tests

```sh
npm test                                   # protocol, transports, wiring and lifecycle, with stubs (no Chromium)
AGENT_BROWSER_E2E=1 npm test               # also drives a real Chromium against a loopback test page
```

The `test_*.js` scripts in this directory are manual diagnostics. `npm test`
does not run them.
