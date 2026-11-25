import assert from "node:assert/strict"
import { mkdtemp, mkdir, writeFile, readFile, readdir, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"

const root = await mkdtemp(join(tmpdir(), "ae-opencode-test-"))
try {
  const skills = join(root, "skills")
  const directory = join(skills, "by-category", "security", "security-audit")
  await mkdir(directory, { recursive: true })
  await writeFile(join(directory, "SKILL.md"), "---\nname: security-audit\n---\nAudit carefully")
  await writeFile(join(skills, "all-skills.json"), JSON.stringify({ skills: [{
    name: "security-audit", category: "security", description: "security audit", tools: [], tags: [],
  }] }))
  process.env.AGENT_SKILLS_DIR = skills
  process.env.AGENT_MEMORY_ROOT = join(root, "memory")
  process.env.AGENT_ENHANCEMENTS_STATE_DIR = join(root, "ae-state")
  process.env.TASK_OBSERVER_WORKSPACE = join(root, "observer")
  const { default: plugin, deliveredTools, runtime, registryCommand } = await import("../opencode-plugin/index.js")
  const stopFlushes = async () => {
    let count = 0
    for (const name of await readdir(join(root, "observer"), { recursive: true }).catch(() => [])) {
      if (name.endsWith("checkpoints.log")) {
        count += (await readFile(join(root, "observer", name), "utf8")).split("\n").filter((line) => line.includes("stop-flush")).length
      }
    }
    return count
  }
  const ref = 'tools["agent-enhancements"].ffmpeg_probe'
  const packaged = "  use: " + ref
  const inventory = { tools: [{ name: "ffmpeg_probe", id: "agent-enhancements_ffmpeg_probe",
    namespace: "agent-enhancements", codemode: true,
    input_schema: { type: "object", properties: { path: { type: "string" } }, required: ["path"] },
  }] }
  const catalog = (declaration) => [{ type: "text", text:
    "## Code Mode tools (call only inside `execute`)\n\n- agent-enhancements (1 tools)\n  - " + declaration }]
  const wire = { tools: { execute: { input: { type: "object", properties: { code: { type: "string" } } } } } }
  assert.equal(deliveredTools(packaged, inventory, { ...wire, system: catalog(ref + "({\n  path: string,\n}): Promise<unknown>") }), true)
  assert.equal(deliveredTools(packaged, inventory, { ...wire, system: catalog(ref + "({\n  wrongParameter: boolean,\n}): Promise<unknown>") }), false)
  assert.equal(deliveredTools(packaged, inventory, { ...wire, system: [{ type: "text", text: "You can use " + ref }] }), false)
  const constrained = { tools: [{ ...inventory.tools[0], input_schema: {
    ...inventory.tools[0].input_schema, additionalProperties: false,
  } }] }
  assert.equal(deliveredTools(packaged, constrained, { ...wire, system: catalog(ref + "({\n  path: string,\n}): Promise<unknown>") }), false)
  const malformed = { tools: [{ ...inventory.tools[0], input_schema: {
    type: "object", properties: { path: null }, required: ["path"],
  } }] }
  assert.equal(deliveredTools(packaged, malformed, { ...wire, system: catalog(ref + "({\n  path: string,\n}): Promise<unknown>") }), false)
  const direct = ["embeddings_embed", "embeddings_embed_batch"].map((name) => ({
    name, id: "agent-enhancements_" + name, namespace: "agent-enhancements", codemode: false,
    input_schema: { type: "object" },
  }))
  const batch = direct[1].id
  const batchOnly = { system: [], tools: { [batch]: { input: direct[1].input_schema } } }
  const compact = "- tool:embeddings-mcp/embeddings_embed_batch [callable] use: " + batch
  assert.equal(deliveredTools("  use: " + batch, { tools: direct }, batchOnly), true)
  assert.equal(deliveredTools(compact, { tools: direct }, batchOnly), true)
  assert.equal(deliveredTools(compact, { tools: direct }, { system: [], tools: {} }), false)
  const large = await runtime({ hook_event_name: "UserPromptSubmit", session_id: "large-inventory", cwd: root,
    prompt: "security audit", ae_host_inventory: { tools: [{ input_schema: { description: "x".repeat(2_001_000) } }] },
  }, true)
  assert.match(large.context, /local skill candidates/)
  const hooks = new Map()
  let disposed = 0
  let mcpPolls = 0
  let toolReloads = 0
  const cleanup = await plugin.setup({
    location: { directory: root, project: { canonical: root } },
    mcp: { list: async () => ({ data: [{ name: "agent-enhancements", status: {
      status: ++mcpPolls === 1 ? "pending" : "connected",
    } }] }) },
    tool: { reload: async () => { toolReloads++ } },
    session: {
      hook: async (name, callback) => {
        hooks.set(name, callback)
        return { dispose: async () => { disposed++ } }
      },
      context: async () => [{ type: "assistant", content: [{ type: "text", text: "completed automated fixture" }] }],
    },
  })
  await hooks.get("prompt")({ sessionID: "session-one", prompt: { text: "security audit" } })
  assert.ok(mcpPolls >= 2)
  assert.equal(toolReloads, 1)
  const request = { sessionID: "session-one", system: [], messages: [] }
  await hooks.get("context")(request)
  assert.match(request.system[0].text, /security-audit/)
  assert.match(request.system[0].text, /registry\.py search/)
  const map = JSON.parse(await readFile(new URL("../../skills/library-map.json", import.meta.url), "utf8")).rendered
  const owned = "<!-- agent-enhancements:begin -->\n## AgentEnhancements library (L0 map)\nRead the map once\n<!-- agent-enhancements:end -->"
  const bootstrap = { sessionID: "session-one", system: [{ type: "text", text: "Keep unrelated instructions.\n" + owned + "\n" + owned }], messages: [] }
  await hooks.get("context")(bootstrap)
  const bootstrapText = bootstrap.system.map((part) => part.text).join("\n")
  // The injected L0 must name the registry by absolute path: the agent runs
  // it from the user's project, where the checkout-relative path fails.
  const absoluteMap = map.replaceAll("python3 unified-integration/scripts/registry.py", registryCommand())
  assert.equal(bootstrapText.split(absoluteMap).length - 1, 1)
  assert.doesNotMatch(bootstrapText, /python3 unified-integration\/scripts\/registry\.py/)
  assert.match(registryCommand(), /^python3 \/.+\/unified-integration\/scripts\/registry\.py$/)
  assert.doesNotMatch(bootstrapText, /agent-enhancements:begin/)
  assert.match(bootstrapText, /Keep unrelated instructions/)
  assert.match(bootstrapText, /historical notes \(7-day TTL\)/)
  assert.match(bootstrapText, /native CLI context compaction/)
  await hooks.get("experimental.idle")({ sessionID: "session-one" })
  await hooks.get("prompt")({ sessionID: "session-two", prompt: { text: "security audit" } })
  const restored = { sessionID: "session-two", system: [], messages: [] }
  await hooks.get("context")(restored)
  assert.match(restored.system[0].text, /completed automated fixture/)
  await hooks.get("prompt")({ sessionID: "session-two", prompt: { text: "security again" } })
  const continued = { sessionID: "session-two", system: [], messages: [] }
  await hooks.get("context")(continued)
  assert.match(continued.system[0].text, /completed automated fixture/)
  // Stop is a turn-end event: tool-loop continuations must not flush it,
  // and one final answer is flushed once (idle or next prompt, not both).
  const said = (text) => [{ role: "user", content: "fix it" }, { role: "assistant", content: text }]
  await hooks.get("prompt")({ sessionID: "session-turns", prompt: { text: "security audit" } })
  const before = await stopFlushes()
  await hooks.get("context")({ sessionID: "session-turns", system: [], messages: said("Let me look at the files first") })
  await hooks.get("context")({ sessionID: "session-turns", system: [], messages: said("Now running the tests") })
  assert.equal(await stopFlushes(), before)
  await hooks.get("experimental.idle")({ sessionID: "session-turns" })
  assert.equal(await stopFlushes(), before + 1)
  await hooks.get("prompt")({ sessionID: "session-turns", prompt: { text: "security again" } })
  await hooks.get("context")({ sessionID: "session-turns", system: [], messages: said("completed automated fixture") })
  await hooks.get("context")({ sessionID: "session-turns", system: [], messages: said("Checking once more") })
  assert.equal(await stopFlushes(), before + 1)
  await hooks.get("prompt")({ sessionID: "session-missed-idle", prompt: { text: "security audit" } })
  await hooks.get("prompt")({ sessionID: "session-missed-idle", prompt: { text: "security again" } })
  await hooks.get("context")({ sessionID: "session-missed-idle", system: [], messages: said("final answer of turn one") })
  assert.equal(await stopFlushes(), before + 2)
  // Idle before the first prompt has no note map entry: dedupe must still hold.
  const idleOnly = await stopFlushes()
  await hooks.get("experimental.idle")({ sessionID: "session-idle-only" })
  await hooks.get("experimental.idle")({ sessionID: "session-idle-only" })
  assert.equal(await stopFlushes(), idleOnly + 1)
  await cleanup()
  assert.equal(disposed, 3)
  const stalledHooks = new Map()
  const cleanupStalled = await plugin.setup({
    location: { directory: root },
    mcp: { list: async () => [{ name: "agent-enhancements", status: { status: "connected" } }] },
    tool: { reload: async () => {}, list: () => new Promise(() => {}) },
    session: { hook: async (name, callback) => {
      stalledHooks.set(name, callback)
      return { dispose: async () => {} }
    } },
  })
  let watchdog
  try {
    await Promise.race([
      stalledHooks.get("prompt")({ sessionID: "stalled-inventory", prompt: { text: "security audit" } }),
      new Promise((_, reject) => { watchdog = setTimeout(() => reject(new Error("host inventory blocked the prompt")), 3500) }),
    ])
    const stalledRequest = { sessionID: "stalled-inventory", system: [], messages: [] }
    await stalledHooks.get("context")(stalledRequest)
    assert.match(stalledRequest.system[0].text, /local skill candidates/)
  } finally {
    clearTimeout(watchdog)
    await cleanupStalled()
  }
  console.log("OpenCode prompt/context/idle integration: OK")
} finally {
  await rm(root, { recursive: true, force: true })
}
