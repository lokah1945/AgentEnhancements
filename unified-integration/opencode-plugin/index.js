import { spawn } from "node:child_process"
import { createHash } from "node:crypto"
import { existsSync, readFileSync, statSync } from "node:fs"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const unified = resolve(dirname(fileURLToPath(import.meta.url)), "..")
const state = process.env.AGENT_ENHANCEMENTS_STATE_DIR || join(unified, "..", ".agentenhancements")
const isolatedPython = join(state, "runtime", "venv", "bin", "python")
const python = existsSync(isolatedPython) ? isolatedPython : "python3"
const maxPrivateInventory = 64000

async function boundedHostRead(operation) {
  let timer
  try {
    return await Promise.race([operation(), new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error("host inventory timeout")), 750)
    })])
  } finally { clearTimeout(timer) }
}

function fileRevision(path) {
  try {
    const info = statSync(path, { bigint: true })
    return `${info.size}:${info.mtimeNs}`
  } catch { return "missing" }
}

function registryStamp() {
  return [join(unified, "skills", "all-skills.json"),
    join(unified, "..", "plugin-catalog", "catalog.json"),
    join(unified, "..", "plugin-catalog", "mcp-servers.json"),
    join(unified, "..", "skills", "library-map.json")].map(fileRevision).join("|")
}

/** Shell-safe absolute command for the registry CLI. The generated L0 map
 * names it relative to the checkout, which fails from a user project. */
export function registryCommand() {
  const script = join(unified, "scripts", "registry.py")
  return "python3 " + (/^[\w\/.-]+$/.test(script) ? script : "'" + script.replaceAll("'", "'\\''") + "'")
}

export function bootstrapMap() {
  try {
    const rendered = JSON.parse(readFileSync(join(unified, "..", "skills", "library-map.json"), "utf8")).rendered
    if (typeof rendered !== "string") return ""
    const map = rendered.replaceAll("python3 unified-integration/scripts/registry.py", registryCommand())
    // Reserve the remainder of the 1,000-token bootstrap slot for the
    // retained workflow rules and wrapper below.
    return Math.floor(map.length / 4) + 1 <= 900 ? map : ""
  } catch { return "" }
}

function lastAssistantText(messages) {
  const last = [...messages].reverse().find((item) => item.role === "assistant" || item.type === "assistant")
  if (!last) return ""
  return typeof last.content === "string" ? last.content :
    (last.content || []).filter((part) => part.type === "text").map((part) => part.text).join("\n")
}

/** Private evidence from this host location, never another gateway process. */
async function hostInventory(ctx, sessionID) {
  if (!ctx.tool?.list || !ctx.mcp?.list) return undefined
  try {
    const api = process.env.AGENT_ENHANCEMENTS_API_FILE || join(unified, "..", "ui.api.json")
    const before = fileRevision(api)
    const [registered, response] = await boundedHostRead(() => Promise.all([ctx.tool.list(), ctx.mcp.list()]))
    const servers = Array.isArray(response) ? response : response.data
    if (!servers?.some((server) => server.name === "agent-enhancements" &&
      server.status.status === "connected") || fileRevision(api) !== before) return undefined
    const inventory = { host: "opencode", session_id: sessionID, source: "ctx.tool.list",
      observed_at: Date.now() / 1000, api_revision: before, gateway: "agent-enhancements",
      tools: registered.filter((tool) => tool.options?.namespace === "agent-enhancements")
        .map((tool) => ({ name: tool.name, id: tool.id, namespace: tool.options.namespace,
          codemode: tool.options.codemode === true, input_schema: tool.input }))
        .sort((a, b) => a.id.localeCompare(b.id)),
    }
    return JSON.stringify(inventory).length <= maxPrivateInventory ? inventory : undefined
  } catch { return undefined }
}

function sameInventory(left, right) {
  return left && right && left.api_revision === right.api_revision &&
    JSON.stringify(left.tools) === JSON.stringify(right.tools)
}

function toolRef(tool) {
  if (!tool.codemode) return tool.id
  const access = /^[a-zA-Z_$][\w$]*$/.test(tool.name) ? `.${tool.name}` : `[${JSON.stringify(tool.name)}]`
  return `tools["agent-enhancements"]${access}`
}

export function deliveredTools(context, inventory, input) {
  const system = input.system.filter((part) => part.type === "text").map((part) => part.text).join("\n")
  const references = new Set([...context.matchAll(/^(?:  use: |- \S+ \[callable\] use: )(.+)$/gm)]
    .flatMap((match) => match[1].split(", ")))
  return (inventory?.tools || []).every((tool) => {
    const ref = toolRef(tool)
    if (!references.has(ref)) return true
    return tool.codemode ? codeModeDelivery(tool, ref, system, input.tools?.execute) :
      JSON.stringify(input.tools?.[tool.id]?.input) === JSON.stringify(tool.input_schema)
  })
}

function codeModeDelivery(tool, ref, system, execute) {
  // Certify the simple primitive-object signatures this MVP can compare
  // completely. More complex Code Mode schemas need host-specific proof;
  // a prose mention, hidden catalog item or lossy approximation is not proof.
  const schema = tool.input_schema
  if (execute?.input?.properties?.code?.type !== "string" || schema.type !== "object" ||
    !schema.properties || !Array.isArray(schema.required) ||
    Object.keys(schema).some((key) => !["type", "properties", "required", "title", "description"].includes(key))) return false
  const fields = []
  for (const [name, property] of Object.entries(schema.properties)) {
    if (!property || typeof property !== "object" || !/^[a-zA-Z_$][\w$]*$/.test(name) || !["string", "number", "boolean"].includes(property.type) ||
      Object.keys(property).some((key) => !["type", "title", "description"].includes(key))) return false
    fields.push(`${name}${schema.required.includes(name) ? "" : "?"}:${property.type},`)
  }
  if (schema.required.some((name) => !Object.hasOwn(schema.properties, name))) return false
  const header = "## Code Mode tools (call only inside `execute`)"
  const start = system.indexOf(header)
  if (start < 0 || system.indexOf(header, start + header.length) >= 0) return false
  const namespaceStart = system.indexOf("\n- agent-enhancements (", start)
  if (namespaceStart < 0) return false
  const nextNamespace = system.indexOf("\n- ", namespaceStart + 1)
  const nextSection = system.indexOf("\n## ", namespaceStart)
  const end = Math.min(...[nextNamespace, nextSection, system.length].filter((index) => index >= 0))
  const catalog = system.slice(namespaceStart, end)
  const prefix = `\n  - ${ref}({\n`
  const declaration = catalog.indexOf(prefix)
  if (declaration < 0 || catalog.indexOf(prefix, declaration + prefix.length) >= 0) return false
  const bodyStart = declaration + prefix.length
  const bodyEnd = catalog.indexOf("\n}): Promise<unknown>", bodyStart)
  if (bodyEnd < 0) return false
  const body = catalog.slice(bodyStart, bodyEnd).replace(/\/\*[\s\S]*?\*\//g, "").replace(/\s+/g, "")
  return body === fields.join("")
}

/** OpenCode connects MCP asynchronously. Wait for our managed server before
 * the first model request captures its immutable tool snapshot. */
async function readyMcp(ctx) {
  if (!ctx.mcp?.list) return
  const deadline = Date.now() + 1500
  try {
    while (Date.now() < deadline) {
      const response = await boundedHostRead(() => ctx.mcp.list())
      const servers = Array.isArray(response) ? response : response.data
      const own = servers.find((server) => server.name === "agent-enhancements")
      if (!own || own.status.status !== "pending") {
        if (own?.status.status === "connected") await boundedHostRead(() => ctx.tool.reload())
        return
      }
      await new Promise((done) => setTimeout(done, 100))
    }
  } catch {
    // A disconnected/disabled MCP must not abort the user's prompt.
  }
}

/** Run the same local event handler as Claude/Codex, without a shell. */
export function runtime(event, bridge = false) {
  return new Promise((done) => {
    const child = spawn(python, [join(unified, "scripts", "runtime.py"), "opencode", bridge ? "--bridge" : "--text"], {
      stdio: ["pipe", "pipe", "ignore"],
    })
    let output = ""
    child.stdout.setEncoding("utf8")
    const empty = bridge ? { context: "", fallback: "" } : ""
    const timer = setTimeout(() => { child.kill(); done(empty) }, 8000)
    child.stdout.on("data", (data) => {
      output += data.toString()
      if (output.length > 24000) { child.kill(); done(empty) }
    })
    child.on("error", () => { clearTimeout(timer); done(empty) })
    child.on("close", () => {
      clearTimeout(timer)
      if (!bridge) return done(output.slice(0, 12000))
      try {
        const value = JSON.parse(output)
        done(typeof value.context === "string" && typeof value.fallback === "string" ? value : empty)
      } catch { done(empty) }
    })
    child.stdin.on("error", () => {})
    // Private proof must never crowd a normally valid prompt out of the
    // runtime's existing input bound, including disabled/fallback turns.
    const ordinary = { ...event }
    delete ordinary.ae_host_inventory
    let payload = JSON.stringify(ordinary)
    try {
      const observed = JSON.stringify(event)
      if (observed.length <= 2_000_000 && observed.length - payload.length <= maxPrivateInventory) payload = observed
    } catch { /* unusable metadata cannot suppress the ordinary event */ }
    child.stdin.end(payload)
  })
}

/** OpenCode 2 Plugin.Definition. Plugin.define() is an identity function;
 * a JavaScript plugin can export the definition without runtime npm packages.
 */
export default {
  id: "agentenhancements",
  async setup(ctx) {
    const notes = new Map()
    // Flush dedupe must outlive the LRU note map: an idle before the first
    // prompt, or after eviction, must still flush each final answer once.
    const flushedDigests = new Map()
    const registrations = []
    const cwd = ctx.location.project?.canonical || ctx.location.directory
    const event = (name, id, extra = {}) => ({
      hook_event_name: name, session_id: id, cwd, ...extra,
    })
    /** Run Stop at most once per distinct final answer of a session. */
    const flush = async (id, text) => {
      if (!text) return
      const digest = createHash("sha256").update(text).digest("hex")
      if (flushedDigests.get(id) === digest) return
      flushedDigests.set(id, digest)
      if (flushedDigests.size > 100) {
        flushedDigests.delete(flushedDigests.keys().next().value)
      }
      await runtime(event("Stop", id, { last_assistant_message: text }))
    }
    registrations.push(await ctx.session.hook("prompt", async (input) => {
      await readyMcp(ctx)
      const id = input.sessionID
      const previous = notes.has(id) ? notes.get(id).previous : await runtime(event("SessionStart", id))
      const inventory = await hostInventory(ctx, id)
      const stamp = registryStamp()
      const prepared = await runtime(event("UserPromptSubmit", id, {
        prompt: input.prompt.text || "", ae_host_inventory: inventory,
      }), true)
      // A new prompt ends the previous turn: its final answer is flushed once,
      // on the first model request of this turn, unless idle already did.
      // Delete before re-inserting so Map order is recency order and the
      // eviction below drops the least recently used session, not an
      // active one (whose loss would repeat SessionStart and drop its flush).
      const old = notes.get(id)
      notes.delete(id)
      notes.set(id, { previous, skills: prepared.context, fallback: prepared.fallback, inventory, stamp,
        pendingFlush: old !== undefined })
      if (notes.size > 100) notes.delete(notes.keys().next().value)
    }))
    registrations.push(await ctx.session.hook("context", async (input) => {
      const context = notes.get(input.sessionID)
      if (context?.skills.startsWith("AgentEnhancements preflight") &&
        (context.stamp !== registryStamp() ||
          (context.inventory && (!sameInventory(context.inventory, await hostInventory(ctx, input.sessionID)) ||
            !deliveredTools(context.skills, context.inventory, input))))) {
        // The existing prepared fallback requires no second UserPromptSubmit.
        context.skills = context.fallback
        console.error("[AgentEnhancements] preflight: custom -> 0 fallback (host_snapshot_changed)")
      }
      // Deliver the existing L0 map itself before inference. Once its contents
      // are available, repeated owned pointer blocks only duplicate bootstrap
      // instructions and encourage an unnecessary second read of the JSON.
      let bootstrap = bootstrapMap()
      if (bootstrap) {
        for (const part of input.system) {
          if (part.type === "text") {
            const original = part.text
            part.text = original.replace(
              /(?:^|\n)Instructions from: [^\n]+\n(?=\s*<!-- agent-enhancements:begin -->)/g, "\n",
            ).replace(/<!-- agent-enhancements:begin -->[\s\S]*?<!-- agent-enhancements:end -->/g, "")
            if (part.text !== original && /^(?:\s*Instructions from: [^\n]+\s*)*$/.test(part.text)) part.text = ""
          }
        }
        const workflow = "Current instructions override historical notes (7-day TTL). " +
          "Never save raw tool I/O or transcripts. Use native CLI context compaction; " +
          "compress.sh only processes standalone files."
        bootstrap = input.system.some((part) => part.type === "text" && part.text.includes(bootstrap)) ?
          workflow : "AgentEnhancements bootstrap (L0):\n" + bootstrap + "\n" + workflow
      }
      const text = [bootstrap, context?.previous, context?.skills].filter(Boolean).join("\n\n")
      if (text) input.system.push({ type: "text", text })
      // Stop is a turn-end event. Tool-loop continuations also reach this
      // hook; running Stop there appended observer checkpoints and replaced
      // the session summary with intermediate text (final audit 2026-11-20).
      if (context?.pendingFlush) {
        context.pendingFlush = false
        await flush(input.sessionID, lastAssistantText(input.messages))
      }
    }))
    registrations.push(await ctx.session.hook("experimental.idle", async (input) => {
      // context() returns the public SessionMessageInfo[] representation.
      // Saving at idle captures the final answer without parsing transcripts.
      try {
        const messages = await ctx.session.context({ sessionID: input.sessionID })
        await flush(input.sessionID, lastAssistantText(messages))
      } catch {
        // A cancelled/deleted session must not fail the agent's lifecycle.
      }
    }))
    return async () => {
      for (const registration of registrations) await registration.dispose()
      notes.clear()
    }
  },
}
