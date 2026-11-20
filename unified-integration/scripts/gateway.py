#!/usr/bin/env python3
"""
AgentEnhancements MCP Gateway — Dynamic MCP server management.
Provides server lifecycle, tool schema validation, health checks, and tool routing.
"""

import json
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import atexit
import signal


class ServerStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    RESTARTING = "restarting"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    id: str
    name: str
    command: List[str]
    env: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    tools: List[str] = field(default_factory=list)
    tools_schema: Optional[Dict] = None
    status: str = "planned"  # planned, available, built
    priority: int = 1  # 1=high, 2=medium, 3=low
    auto_start: bool = False
    health_check_interval: int = 30  # seconds
    restart_on_failure: bool = True
    max_restarts: int = 3


@dataclass
class MCPServerInstance:
    """Runtime instance of an MCP server."""
    config: MCPServerConfig
    process: Optional[subprocess.Popen] = None
    status: ServerStatus = ServerStatus.STOPPED
    started_at: Optional[float] = None
    last_health_check: Optional[float] = None
    health_status: str = "unknown"
    tools_cache: Dict = field(default_factory=dict)
    restart_count: int = 0
    error_message: str = ""


class MCPGateway:
    """
    MCP Gateway managing multiple MCP servers.
    Handles lifecycle, tool discovery, schema validation, and request routing.
    """

    def __init__(self, base_dir: Path, config: Optional[Dict] = None):
        self.base_dir = base_dir
        self.config = config or {}
        self.servers: Dict[str, MCPServerInstance] = {}
        self._lock = threading.RLock()
        self._health_check_thread: Optional[threading.Thread] = None
        self._shutdown = False

        # Load server configurations
        self._load_server_configs()

        # Register cleanup on exit
        atexit.register(self.shutdown)

    def _load_server_configs(self):
        """Load MCP server configurations from catalog."""
        mcp_path = self.base_dir / "plugin-catalog" / "mcp-servers.json"
        if not mcp_path.exists():
            return

        try:
            data = json.loads(mcp_path.read_text())
            servers_data = data.get("mcp-servers", {})

            for sid, sdata in servers_data.items():
                config = MCPServerConfig(
                    id=sid,
                    name=sdata.get("description", sid),
                    command=sdata.get("command", []),
                    env=sdata.get("env", {}),
                    description=sdata.get("description", ""),
                    tools=sdata.get("tools", []),
                    status=sdata.get("status", "planned"),
                )
                # Resolve environment variables
                config.env = self._resolve_env(config.env)
                self.servers[sid] = MCPServerInstance(config=config)
        except Exception as e:
            print(f"Failed to load MCP configs: {e}", file=sys.stderr)

    def _resolve_env(self, env: Dict[str, str]) -> Dict[str, str]:
        """Resolve ${VAR} references in environment values."""
        resolved = {}
        for k, v in env.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                var_name = v[2:-1]
                resolved[k] = os.getenv(var_name, "")
            else:
                resolved[k] = v
        return resolved

    # =========================================================================
    # SERVER LIFECYCLE
    # =========================================================================
    def start_server(self, server_id: str) -> bool:
        """Start an MCP server."""
        with self._lock:
            instance = self.servers.get(server_id)
            if not instance:
                return False

            if instance.status in (ServerStatus.RUNNING, ServerStatus.STARTING):
                return True

            instance.status = ServerStatus.STARTING
            instance.error_message = ""

            try:
                # Prepare environment
                env = os.environ.copy()
                env.update(instance.config.env)

                # Start process
                instance.process = subprocess.Popen(
                    instance.config.command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True,
                    bufsize=1,
                )

                instance.started_at = time.time()
                instance.status = ServerStatus.RUNNING

                # Initialize server (send initialize request)
                self._initialize_server(instance)

                # Cache tools
                self._cache_tools(instance)

                # Start health check if not running
                if not self._health_check_thread or not self._health_check_thread.is_alive():
                    self._start_health_checks()

                return True

            except Exception as e:
                instance.status = ServerStatus.ERROR
                instance.error_message = str(e)
                return False

    def stop_server(self, server_id: str) -> bool:
        """Stop an MCP server."""
        with self._lock:
            instance = self.servers.get(server_id)
            if not instance:
                return False

            if instance.status == ServerStatus.STOPPED:
                return True

            try:
                if instance.process:
                    instance.process.terminate()
                    try:
                        instance.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        instance.process.kill()
                        instance.process.wait()

                instance.process = None
                instance.status = ServerStatus.STOPPED
                instance.tools_cache = {}
                return True

            except Exception as e:
                instance.error_message = str(e)
                return False

    def restart_server(self, server_id: str) -> bool:
        """Restart an MCP server."""
        self.stop_server(server_id)
        time.sleep(1)
        return self.start_server(server_id)

    def _initialize_server(self, instance: MCPServerInstance):
        """Send initialize request to MCP server."""
        if not instance.process or not instance.process.stdin:
            return

        init_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ae-gateway", "version": "1.0.0"}
            }
        }

        try:
            instance.process.stdin.write(json.dumps(init_request) + "\n")
            instance.process.stdin.flush()

            # Read response (with timeout)
            import select
            ready, _, _ = select.select([instance.process.stdout], [], [], 5)
            if ready:
                line = instance.process.stdout.readline()
                response = json.loads(line)
                # Could validate response here
        except Exception:
            pass  # Non-fatal

    def _cache_tools(self, instance: MCPServerInstance):
        """Fetch and cache tool schemas from server."""
        if not instance.process or not instance.process.stdin:
            return

        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {}
        }

        try:
            instance.process.stdin.write(json.dumps(request) + "\n")
            instance.process.stdin.flush()

            import select
            ready, _, _ = select.select([instance.process.stdout], [], [], 5)
            if ready:
                line = instance.process.stdout.readline()
                response = json.loads(line)
                if "result" in response and "tools" in response["result"]:
                    tools = response["result"]["tools"]
                    instance.tools_cache = {t["name"]: t for t in tools}
        except Exception:
            pass

    # =========================================================================
    # TOOL OPERATIONS
    # =========================================================================
    def list_tools(self, server_id: Optional[str] = None) -> Dict[str, List[Dict]]:
        """List available tools from all servers or a specific server."""
        with self._lock:
            result = {}
            servers = [self.servers[server_id]] if server_id else self.servers.values()

            for instance in servers:
                if instance.status == ServerStatus.RUNNING and instance.tools_cache:
                    result[instance.config.id] = list(instance.tools_cache.values())
            return result

    def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Call a tool on an MCP server."""
        with self._lock:
            instance = self.servers.get(server_id)
            if not instance:
                return {"error": f"Server not found: {server_id}"}

            if instance.status != ServerStatus.RUNNING:
                # Try to start
                if not self.start_server(server_id):
                    return {"error": f"Server not running: {server_id}"}

            if not instance.process or not instance.process.stdin:
                return {"error": "Server process not available"}

            # Validate tool exists
            if tool_name not in instance.tools_cache:
                return {"error": f"Tool not found: {tool_name}"}

            # Validate arguments against schema
            tool_schema = instance.tools_cache[tool_name].get("inputSchema")
            if tool_schema:
                validation_error = self._validate_arguments(arguments, tool_schema)
                if validation_error:
                    return {"error": f"Invalid arguments: {validation_error}"}

            # Send tool call
            request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            try:
                instance.process.stdin.write(json.dumps(request) + "\n")
                instance.process.stdin.flush()

                import select
                ready, _, _ = select.select([instance.process.stdout], [], [], timeout)
                if not ready:
                    return {"error": "Tool call timeout"}

                line = instance.process.stdout.readline()
                response = json.loads(line)

                if "error" in response:
                    return {"error": response["error"]}

                return response.get("result", {})

            except Exception as e:
                return {"error": f"Tool call failed: {e}"}

    def _validate_arguments(self, args: Dict, schema: Dict) -> Optional[str]:
        """Validate arguments against JSON schema (basic validation)."""
        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in args:
                return f"Missing required field: {field}"

        # Check types (basic)
        properties = schema.get("properties", {})
        for key, value in args.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type and not self._check_type(value, expected_type):
                    return f"Field {key}: expected {expected_type}, got {type(value).__name__}"

        return None

    def _check_type(self, value: Any, expected: str) -> bool:
        """Basic type checking."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected_type = type_map.get(expected)
        if expected_type:
            return isinstance(value, expected_type)
        return True

    # =========================================================================
    # HEALTH CHECKS
    # =========================================================================
    def _start_health_checks(self):
        """Start background health check thread."""
        if self._health_check_thread and self._health_check_thread.is_alive():
            return

        self._shutdown = False
        self._health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_check_thread.start()

    def _health_check_loop(self):
        """Background health check loop."""
        while not self._shutdown:
            time.sleep(10)  # Check every 10 seconds

            with self._lock:
                for instance in self.servers.values():
                    if instance.status == ServerStatus.RUNNING:
                        self._check_server_health(instance)

    def _check_server_health(self, instance: MCPServerInstance):
        """Check health of a single server."""
        now = time.time()

        # Check if process is alive
        if instance.process and instance.process.poll() is not None:
            # Process died
            instance.status = ServerStatus.ERROR
            instance.error_message = "Process terminated unexpectedly"

            # Attempt restart if configured
            if instance.config.restart_on_failure and instance.restart_count < instance.config.max_restarts:
                instance.status = ServerStatus.RESTARTING
                instance.restart_count += 1
                self.restart_server(instance.config.id)
            return

        # Send health check ping
        if instance.process and instance.process.stdin:
            try:
                request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "health",
                    "params": {}
                }
                instance.process.stdin.write(json.dumps(request) + "\n")
                instance.process.stdin.flush()

                import select
                ready, _, _ = select.select([instance.process.stdout], [], [], 5)
                if ready:
                    line = instance.process.stdout.readline()
                    response = json.loads(line)
                    if response.get("result", {}).get("status") == "ok":
                        instance.health_status = "healthy"
                        instance.last_health_check = now
                        return
            except Exception:
                pass

        instance.health_status = "unhealthy"

    def get_server_status(self, server_id: str) -> Optional[Dict]:
        """Get status of a server."""
        with self._lock:
            instance = self.servers.get(server_id)
            if not instance:
                return None

            return {
                "id": instance.config.id,
                "name": instance.config.name,
                "status": instance.status.value,
                "health": instance.health_status,
                "started_at": instance.started_at,
                "last_health_check": instance.last_health_check,
                "restart_count": instance.restart_count,
                "error": instance.error_message,
                "tools_count": len(instance.tools_cache),
            }

    def get_all_status(self) -> List[Dict]:
        """Get status of all servers."""
        with self._lock:
            return [self.get_server_status(sid) for sid in self.servers]

    # =========================================================================
    # AUTO-START & SHUTDOWN
    # =========================================================================
    def auto_start_servers(self, priority: int = 1) -> int:
        """Auto-start servers with priority <= given priority."""
        started = 0
        with self._lock:
            for instance in self.servers.values():
                if instance.config.auto_start and instance.config.priority <= priority:
                    if self.start_server(instance.config.id):
                        started += 1
        return started

    def shutdown(self):
        """Shutdown all servers and cleanup."""
        self._shutdown = True

        with self._lock:
            for instance in self.servers.values():
                if instance.status == ServerStatus.RUNNING:
                    self.stop_server(instance.config.id)

        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)


# =========================================================================
# BUILT-IN MCP SERVERS (Python implementations)
# =========================================================================
class BuiltinMCPServer:
    """Base class for built-in MCP servers implemented in Python."""

    def __init__(self, name: str):
        self.name = name
        self.tools = {}

    def register_tool(self, name: str, description: str, schema: Dict, handler):
        """Register a tool."""
        self.tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": schema,
            "handler": handler
        }

    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming JSON-RPC request."""
        method = request.get("method")
        req_id = request.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": self.name, "version": "1.0.0"}
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": [
                    {"name": k, "description": v["description"], "inputSchema": v["inputSchema"]}
                    for k, v in self.tools.items()
                ]}
            }

        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name")
            args = params.get("arguments", {})

            if tool_name not in self.tools:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
                }

            try:
                result = self.tools[tool_name]["handler"](args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": result
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": str(e)}
                }

        elif method == "health":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"status": "ok", "server": self.name}
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }

    def run_stdio(self):
        """Run server over stdio."""
        import sys
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                print(json.dumps(response), flush=True)
            except Exception as e:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {e}"}
                }), flush=True)


# =========================================================================
# PRIORITY BUILT-IN SERVERS
# =========================================================================
class FilesystemMCPServer(BuiltinMCPServer):
    """Filesystem operations MCP server."""

    def __init__(self):
        super().__init__("filesystem")
        self.register_tool(
            "read_file",
            "Read a file from the filesystem",
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            self._read_file
        )
        self.register_tool(
            "write_file",
            "Write a file to the filesystem",
            {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
            self._write_file
        )
        self.register_tool(
            "list_dir",
            "List directory contents",
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            self._list_dir
        )
        self.register_tool(
            "glob",
            "Find files matching a pattern",
            {"type": "object", "properties": {"pattern": {"type": "string"}, "root": {"type": "string"}}, "required": ["pattern"]},
            self._glob
        )

    def _read_file(self, args: Dict) -> Dict:
        path = Path(args["path"]).resolve()
        if not path.exists():
            return {"error": f"File not found: {path}"}
        return {"content": path.read_text(encoding="utf-8")}

    def _write_file(self, args: Dict) -> Dict:
        path = Path(args["path"]).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"], encoding="utf-8")
        return {"success": True, "path": str(path)}

    def _list_dir(self, args: Dict) -> Dict:
        path = Path(args["path"]).resolve()
        if not path.exists():
            return {"error": f"Directory not found: {path}"}
        return {"entries": [{"name": p.name, "type": "dir" if p.is_dir() else "file"} for p in path.iterdir()]}

    def _glob(self, args: Dict) -> Dict:
        root = Path(args.get("root", ".")).resolve()
        pattern = args["pattern"]
        matches = list(root.rglob(pattern))
        return {"matches": [str(p.relative_to(root)) for p in matches]}


class GitMCPServer(BuiltinMCPServer):
    """Git operations MCP server."""

    def __init__(self):
        super().__init__("git")
        self.register_tool(
            "git_status",
            "Get git status",
            {"type": "object", "properties": {"repo_path": {"type": "string"}}, "required": []},
            self._status
        )
        self.register_tool(
            "git_log",
            "Get git log",
            {"type": "object", "properties": {"repo_path": {"type": "string"}, "limit": {"type": "integer"}}, "required": []},
            self._log
        )
        self.register_tool(
            "git_diff",
            "Get git diff",
            {"type": "object", "properties": {"repo_path": {"type": "string"}, "file": {"type": "string"}}, "required": []},
            self._diff
        )

    def _run_git(self, args: List[str], repo_path: str = ".") -> str:
        result = subprocess.run(["git"] + args, cwd=repo_path, capture_output=True, text=True)
        return result.stdout

    def _status(self, args: Dict) -> Dict:
        repo = args.get("repo_path", ".")
        return {"output": self._run_git(["status"], repo)}

    def _log(self, args: Dict) -> Dict:
        repo = args.get("repo_path", ".")
        limit = args.get("limit", 10)
        return {"output": self._run_git(["log", "--oneline", f"-{limit}"], repo)}

    def _diff(self, args: Dict) -> Dict:
        repo = args.get("repo_path", ".")
        file = args.get("file")
        cmd = ["diff"] + ([file] if file else [])
        return {"output": self._run_git(cmd, repo)}


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="MCP Gateway CLI")
    parser.add_argument("command", choices=["start", "stop", "restart", "status", "list-tools", "call", "auto-start", "run-builtin"])
    parser.add_argument("--server", help="Server ID")
    parser.add_argument("--tool", help="Tool name")
    parser.add_argument("--args", help="Tool arguments (JSON)")
    parser.add_argument("--priority", type=int, default=1)
    parser.add_argument("--builtin", choices=["filesystem", "git"], help="Built-in server to run")

    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    gateway = MCPGateway(base_dir)

    if args.command == "run-builtin":
        if args.builtin == "filesystem":
            FilesystemMCPServer().run_stdio()
        elif args.builtin == "git":
            GitMCPServer().run_stdio()
        return

    if args.command == "start":
        if not args.server:
            parser.error("--server required")
        ok = gateway.start_server(args.server)
        print("OK" if ok else "FAILED")

    elif args.command == "stop":
        if not args.server:
            parser.error("--server required")
        ok = gateway.stop_server(args.server)
        print("OK" if ok else "FAILED")

    elif args.command == "restart":
        if not args.server:
            parser.error("--server required")
        ok = gateway.restart_server(args.server)
        print("OK" if ok else "FAILED")

    elif args.command == "status":
        if args.server:
            print(json.dumps(gateway.get_server_status(args.server), indent=2))
        else:
            print(json.dumps(gateway.get_all_status(), indent=2))

    elif args.command == "list-tools":
        print(json.dumps(gateway.list_tools(args.server), indent=2))

    elif args.command == "call":
        if not args.server or not args.tool:
            parser.error("--server and --tool required")
        tool_args = json.loads(args.args) if args.args else {}
        result = gateway.call_tool(args.server, args.tool, tool_args)
        print(json.dumps(result, indent=2))

    elif args.command == "auto-start":
        count = gateway.auto_start_servers(args.priority)
        print(f"Started {count} servers")


if __name__ == "__main__":
    main()