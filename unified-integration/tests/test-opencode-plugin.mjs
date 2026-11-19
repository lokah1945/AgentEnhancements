import assert from "node:assert/strict"
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises"
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
  const { default: plugin } = await import("../opencode-plugin/index.js")
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
  await hooks.get("experimental.idle")({ sessionID: "session-one" })
  await hooks.get("prompt")({ sessionID: "session-two", prompt: { text: "security audit" } })
  const restored = { sessionID: "session-two", system: [], messages: [] }
  await hooks.get("context")(restored)
  assert.match(restored.system[0].text, /completed automated fixture/)
  await hooks.get("prompt")({ sessionID: "session-two", prompt: { text: "security again" } })
  const continued = { sessionID: "session-two", system: [], messages: [] }
  await hooks.get("context")(continued)
  assert.match(continued.system[0].text, /completed automated fixture/)
  await cleanup()
  assert.equal(disposed, 3)
  console.log("OpenCode prompt/context/idle integration: OK")
} finally {
  await rm(root, { recursive: true, force: true })
}
