import { spawn } from "node:child_process"
import { existsSync } from "node:fs"
import { homedir } from "node:os"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const unified = resolve(dirname(fileURLToPath(import.meta.url)), "..")
const dataHome = process.env.XDG_DATA_HOME || join(homedir(), ".local", "share")
const isolatedPython = join(dataHome, "agentenhancements", "venv", "bin", "python")
const python = existsSync(isolatedPython) ? isolatedPython : "python3"

/** Run the same local event handler as Claude/Codex, without a shell. */
export function runtime(event) {
  return new Promise((done) => {
    const child = spawn(python, [join(unified, "scripts", "runtime.py"), "opencode", "--text"], {
      stdio: ["pipe", "pipe", "ignore"],
    })
    let output = ""
    child.stdout.setEncoding("utf8")
    const timer = setTimeout(() => { child.kill(); done("") }, 8000)
    child.stdout.on("data", (data) => { output += data.toString() })
    child.on("error", () => { clearTimeout(timer); done("") })
    child.on("close", () => { clearTimeout(timer); done(output.slice(0, 12000)) })
    child.stdin.on("error", () => {})
    child.stdin.end(JSON.stringify(event))
  })
}

/** OpenCode 2 Plugin.Definition. Plugin.define() is an identity function;
 * a JavaScript plugin can export the definition without runtime npm packages.
 */
export default {
  id: "agentenhancements",
  async setup(ctx) {
    const notes = new Map()
    const registrations = []
    const cwd = ctx.location.project?.canonical || ctx.location.directory
    const event = (name, id, extra = {}) => ({
      hook_event_name: name, session_id: id, cwd, ...extra,
    })
    registrations.push(await ctx.session.hook("prompt", async (input) => {
      const id = input.sessionID
      const previous = notes.has(id) ? notes.get(id).previous : await runtime(event("SessionStart", id))
      const skills = await runtime(event("UserPromptSubmit", id, { prompt: input.prompt.text || "" }))
      notes.set(id, { previous, skills })
      if (notes.size > 100) notes.delete(notes.keys().next().value)
    }))
    registrations.push(await ctx.session.hook("context", async (input) => {
      const context = notes.get(input.sessionID)
      const text = context && [context.previous, context.skills].filter(Boolean).join("\n\n")
      if (text) input.system.push({ type: "text", text })
      const last = [...input.messages].reverse().find((item) => item.role === "assistant")
      if (last) {
        const text = typeof last.content === "string" ? last.content :
          (last.content || []).filter((part) => part.type === "text").map((part) => part.text).join("\n")
        if (text) await runtime(event("Stop", input.sessionID, { last_assistant_message: text }))
      }
    }))
    registrations.push(await ctx.session.hook("experimental.idle", async (input) => {
      // context() returns the public SessionMessageInfo[] representation.
      // Saving at idle captures the final answer without parsing transcripts.
      try {
        const messages = await ctx.session.context({ sessionID: input.sessionID })
        const last = [...messages].reverse().find((item) => item.type === "assistant")
        const text = (last?.content || []).filter((part) => part.type === "text").map((part) => part.text).join("\n")
        if (text) await runtime(event("Stop", input.sessionID, { last_assistant_message: text }))
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
