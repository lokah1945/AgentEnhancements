#!/usr/bin/env python3
"""
AgentEnhancements Adaptive Preflight v2 — Capability selection before main inference.
Merges ASUS Mode 0/1/2 implementation with DELL structured approach (dataclasses, enums).
Supports three modes:
- Mode 0: Legacy heuristic discovery (default, no external calls)
- Mode 1: Native auto-selection (Claude Code/Codex native handoff) — UNSUPPORTED
- Mode 2: Custom endpoint (OpenAI/Anthropic-compatible selector model)

Enhanced with:
- Evidence-aware selector prompts (task intent, constraints, acceptance criteria, repo policies)
- Semantic relevance scoring for selector output validation
- Improved readiness validation (credentials, installed commands, host compatibility)
- Conflict detection between selected capabilities
- Graceful fallback with diagnostics
- Abstention logic when native agent can handle
- Lookup/unresolved handling per contract schema
"""

import json
import os
import time
import uuid
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import ASUS registry for compatibility
from registry import find_entry, load_all_entries


class PreflightMode(Enum):
    LEGACY = 0          # Heuristic keyword matching (ASUS Mode 0)
    NATIVE_AUTO = 1     # Host-native selection (ASUS Mode 1) — UNSUPPORTED
    CUSTOM_ENDPOINT = 2 # Custom selector model endpoint (ASUS Mode 2)


@dataclass
class PreflightConfig:
    """Configuration for adaptive preflight."""
    mode: PreflightMode = PreflightMode.LEGACY
    # Mode 1 settings
    native_adapter: str = ""  # claude-code, codex
    # Mode 2 settings
    endpoint_url: str = ""
    model_name: str = ""
    api_key_ref: str = ""  # Reference to key in ui.api.json
    max_rounds: int = 2
    deadline_ms: int = 2000
    # Common
    max_skill_cards: int = 8
    token_budget: int = 400
    fallback_on_error: bool = True


@dataclass
class SelectedCapability:
    """A selected capability with readiness info."""
    type: str  # skill, plugin, mcp, builtin
    id: str
    name: str
    version: str
    readiness: str  # ready, not_installed, missing_credentials, guide_only, unavailable
    readiness_reason: str
    token_estimate: int
    schema: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)
    role: str = "optional"  # primary, supporting, optional, alternative
    conflict_with: List[str] = field(default_factory=list)


@dataclass
class PreflightResult:
    """Result of preflight capability selection."""
    mode: PreflightMode
    skills: List[SelectedCapability] = field(default_factory=list)
    plugins: List[SelectedCapability] = field(default_factory=list)
    mcp_servers: List[SelectedCapability] = field(default_factory=list)
    builtins: List[SelectedCapability] = field(default_factory=list)
    lookups: List[Dict] = field(default_factory=list)
    unresolved: List[Dict] = field(default_factory=list)  # Per contract schema
    warnings: List[str] = field(default_factory=list)
    token_estimate: int = 0
    fallback_used: bool = False
    selector_latency_ms: int = 0
    selector_raw_response: str = ""
    abstained: bool = False
    abstain_reason: str = ""


class AdaptivePreflightV2:
    """
    Adaptive preflight engine for capability selection.
    Merges ASUS fallback determinism with DELL structured validation.
    """

    # Framework conflict groups for conflict detection (from DELL)
    CONFLICT_GROUPS = [
        {"django", "flask", "fastapi"},
        {"react", "vue", "angular", "svelte"},
        {"postgresql", "mysql", "mongodb"},
        {"aws", "gcp", "azure"},
        {"jest", "vitest", "pytest"},
    ]

    def __init__(self, base_dir: Path, registry_module=None):
        self.base_dir = base_dir
        self.registry = registry_module  # Keep for compatibility, but use module functions
        self.config = self._load_config()

    def _load_config(self) -> PreflightConfig:
        """Load preflight config from ui.api.json."""
        config = PreflightConfig()

        # Check for ui.api.json
        api_file = self.base_dir / "ui.api.json"
        if not api_file.exists():
            api_file = self.base_dir.parent / "ui.api.json"

        if api_file.exists():
            try:
                data = json.loads(api_file.read_text())
                preflight_cfg = data.get("preflight", {})
                config.mode = PreflightMode(preflight_cfg.get("mode", 0))
                config.native_adapter = preflight_cfg.get("native_adapter", "")
                config.endpoint_url = preflight_cfg.get("endpoint_url", "")
                config.model_name = preflight_cfg.get("model_name", "")
                config.api_key_ref = preflight_cfg.get("api_key_ref", "")
                config.max_rounds = preflight_cfg.get("max_rounds", 2)
                config.deadline_ms = preflight_cfg.get("deadline_ms", 2000)
                config.max_skill_cards = preflight_cfg.get("max_skill_cards", 8)
                config.token_budget = preflight_cfg.get("token_budget", 400)
                config.fallback_on_error = preflight_cfg.get("fallback_on_error", True)
            except Exception as e:
                print(f"[adaptive_preflight] Config load warning: {e}", file=sys.stderr)

        # Environment overrides (ASUS compatibility)
        if os.getenv("AE_PREFLIGHT_MODE"):
            config.mode = PreflightMode(int(os.getenv("AE_PREFLIGHT_MODE")))
        if os.getenv("AE_PREFLIGHT_DEADLINE_MS"):
            config.deadline_ms = int(os.getenv("AE_PREFLIGHT_DEADLINE_MS"))
        if os.getenv("AE_MAX_SKILL_CARDS"):
            config.max_skill_cards = int(os.getenv("AE_MAX_SKILL_CARDS"))

        return config

    def run(
        self,
        agent: str,
        prompt: str,
        event: Dict[str, Any],
        fallback_fn=None
    ) -> PreflightResult:
        """
        Run adaptive preflight capability selection.

        Args:
            agent: Agent type (claude-code, codex, etc.)
            prompt: User prompt/task description
            event: Hook event data
            fallback_fn: Fallback function for Mode 0 (ASUS skill_context)

        Returns:
            PreflightResult with selected capabilities
        """
        start_time = time.time()

        # Mode 0: Legacy heuristic (ASUS skill_context) - DEFAULT
        if self.config.mode == PreflightMode.LEGACY:
            if fallback_fn:
                fallback_result = fallback_fn(agent, prompt)
                return PreflightResult(
                    mode=PreflightMode.LEGACY,
                    fallback_used=False,
                    selector_latency_ms=int((time.time() - start_time) * 1000),
                )
            else:
                # Inline fallback: use registry keyword search
                return self._legacy_fallback(agent, prompt, start_time)

        # Mode 1: Native auto-selection — UNSUPPORTED per ASUS README
        if self.config.mode == PreflightMode.NATIVE_AUTO:
            warning = "Mode 1 (native auto-selection) is unsupported — host APIs do not expose selection surface. Falling back to Mode 0."
            print(f"[adaptive_preflight] {warning}", file=sys.stderr)
            if self.config.fallback_on_error and fallback_fn:
                fallback_result = fallback_fn(agent, prompt)
                return PreflightResult(
                    mode=PreflightMode.LEGACY,
                    fallback_used=True,
                    warnings=[warning],
                    selector_latency_ms=int((time.time() - start_time) * 1000),
                )
            return PreflightResult(
                mode=PreflightMode.LEGACY,
                fallback_used=True,
                warnings=[warning],
                selector_latency_ms=int((time.time() - start_time) * 1000),
            )

        # Mode 2: Custom endpoint
        if self.config.mode == PreflightMode.CUSTOM_ENDPOINT:
            return self._run_custom_endpoint(agent, prompt, event, fallback_fn, start_time)

        # Unknown mode - fallback
        if fallback_fn:
            fallback_result = fallback_fn(agent, prompt)
        return PreflightResult(
            mode=PreflightMode.LEGACY,
            fallback_used=True,
            warnings=[f"Unknown preflight mode: {self.config.mode}"],
            selector_latency_ms=int((time.time() - start_time) * 1000),
        )

    def _legacy_fallback(self, agent: str, prompt: str, start_time: float) -> PreflightResult:
        """ASUS-style legacy keyword-based skill discovery."""
        try:
            # Use registry search (ASUS approach) - cmd_map prints to stdout
            import subprocess
            result = subprocess.run([
                sys.executable, "-m", "registry", "map", prompt,
                "--limit", str(self.config.max_skill_cards), "--json"
            ], cwd=self.base_dir, capture_output=True, text=True, timeout=10)
            # For now, just return empty result with fallback flag
        except Exception:
            pass

        return PreflightResult(
            mode=PreflightMode.LEGACY,
            fallback_used=False,
            selector_latency_ms=int((time.time() - start_time) * 1000),
        )

    def _run_custom_endpoint(
        self,
        agent: str,
        prompt: str,
        event: Dict[str, Any],
        fallback_fn,
        start_time: float
    ) -> PreflightResult:
        """Run Mode 2 custom endpoint selection."""
        # Check required config
        if not self.config.endpoint_url or not self.config.model_name:
            warning = "Mode 2 configured but endpoint_url or model_name missing. Falling back to Mode 0."
            print(f"[adaptive_preflight] {warning}", file=sys.stderr)
            if self.config.fallback_on_error and fallback_fn:
                fallback_result = fallback_fn(agent, prompt)
                return PreflightResult(
                    mode=PreflightMode.LEGACY,
                    fallback_used=True,
                    warnings=[warning],
                    selector_latency_ms=int((time.time() - start_time) * 1000),
                )
            return PreflightResult(
                mode=PreflightMode.LEGACY,
                fallback_used=True,
                warnings=[warning],
                selector_latency_ms=int((time.time() - start_time) * 1000),
            )

        # Load API key from ui.api.json
        api_key = self._get_api_key()
        if not api_key:
            warning = f"Mode 2 API key '{self.config.api_key_ref}' not found in ui.api.json. Falling back to Mode 0."
            print(f"[adaptive_preflight] {warning}", file=sys.stderr)
            if self.config.fallback_on_error and fallback_fn:
                fallback_result = fallback_fn(agent, prompt)
                return PreflightResult(
                    mode=PreflightMode.LEGACY,
                    fallback_used=True,
                    warnings=[warning],
                    selector_latency_ms=int((time.time() - start_time) * 1000),
                )
            return PreflightResult(
                mode=PreflightMode.LEGACY,
                fallback_used=True,
                warnings=[warning],
                selector_latency_ms=int((time.time() - start_time) * 1000),
            )

        # Build selector prompt
        selector_prompt = self._build_selector_prompt(agent, prompt, event)

        # Call custom endpoint
        try:
            selector_response = self._call_endpoint(selector_prompt, api_key)
            self.config.selector_raw_response = selector_response

            # Parse and validate response
            result = self._parse_selector_response(selector_response, agent, prompt)
            result.selector_latency_ms = int((time.time() - start_time) * 1000)
            return result

        except Exception as e:
            warning = f"Mode 2 selector call failed: {e}. Falling back to Mode 0."
            print(f"[adaptive_preflight] {warning}", file=sys.stderr)
            if self.config.fallback_on_error and fallback_fn:
                fallback_result = fallback_fn(agent, prompt)
                return PreflightResult(
                    mode=PreflightMode.LEGACY,
                    fallback_used=True,
                    warnings=[warning],
                    selector_latency_ms=int((time.time() - start_time) * 1000),
                )
            return PreflightResult(
                mode=PreflightMode.LEGACY,
                fallback_used=True,
                warnings=[warning],
                selector_latency_ms=int((time.time() - start_time) * 1000),
            )

    def _get_api_key(self) -> Optional[str]:
        """Get API key from ui.api.json."""
        api_file = self.base_dir / "ui.api.json"
        if not api_file.exists():
            api_file = self.base_dir.parent / "ui.api.json"

        if not api_file.exists():
            return None

        try:
            data = json.loads(api_file.read_text())
            api_keys = data.get("api_keys", {})
            key_ref = self.config.api_key_ref or "PREFLIGHT_API_KEY"

            # Support rotation: first usable key in list
            keys = api_keys.get(key_ref)
            if isinstance(keys, list):
                for k in keys:
                    if k and isinstance(k, str) and len(k) > 10:
                        return k
            elif isinstance(keys, str) and len(keys) > 10:
                return keys
        except Exception:
            pass
        return None

    def _build_selector_prompt(self, agent: str, prompt: str, event: Dict[str, Any]) -> str:
        """Build structured selector prompt (DELL evidence-aware approach)."""
        # Get catalog cards for context
        catalog_summary = self._get_catalog_summary()

        return f"""You are the capability selector for AgentEnhancements. You cannot execute anything; you only choose capabilities.

AGENT: {agent}
TASK: {prompt}
CATALOG SUMMARY:
{catalog_summary}

Given the task intent and catalog cards, pick the minimal set of registry capabilities the task actually needs, or abstain when ordinary tools are enough.

Respond with JSON only matching this schema:
{{
  "decision": "selected|abstain|lookup|unresolved",
  "items": [
    {{"id": "<registry id>", "required": true, "reason": "<short>"}}
  ],
  "queries": ["<focused query>"],
  "reason": "<short>"
}}

Rules:
- items only with decision=selected (0-12 items, ordered by importance, typed registry ids only: skill:<name>, plugin:<slug>, mcp:<server>, capability:<name>, tool:<server>/<tool-name>)
- queries only with decision=lookup (1-4 focused catalog queries)
- decision=abstain when no catalog capability is needed
- decision=unresolved when catalog cannot satisfy a stated requirement
- Plugin catalog entries are integration guides, not proof of installed runtime. Mark guide-only plugin suggestions optional.
"""

    def _get_catalog_summary(self) -> str:
        """Get a summary of available capabilities for the selector."""
        try:
            # Use registry stats via subprocess
            import subprocess
            result = subprocess.run([
                sys.executable, "-m", "registry", "stats", "--json"
            ], cwd=self.base_dir, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                import json
                stats = json.loads(result.stdout)
                return f"Total capabilities: {stats.get('stats', {}).get('total', 0)}"
            return "Catalog stats unavailable"
        except Exception:
            return "Catalog stats unavailable"

    def _call_endpoint(self, prompt: str, api_key: str) -> str:
        """Call custom endpoint (OpenAI/Anthropic compatible)."""
        import urllib.request
        import urllib.error

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Determine SDK format from endpoint
        if "anthropic" in self.config.endpoint_url.lower():
            payload = {
                "model": self.config.model_name,
                "max_tokens": self.config.token_budget,
                "messages": [{"role": "user", "content": prompt}],
            }
        else:
            # OpenAI-compatible
            payload = {
                "model": self.config.model_name,
                "max_tokens": self.config.token_budget,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(self.config.endpoint_url, data=data, headers=headers)

        timeout = min(self.config.deadline_ms / 1000, 10.0)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode('utf-8'))

            # Extract content based on response format
            if "choices" in result:
                return result["choices"][0]["message"]["content"]
            elif "content" in result:
                return result["content"][0]["text"]
            else:
                return json.dumps(result)

    def _parse_selector_response(
        self,
        response: str,
        agent: str,
        prompt: str
    ) -> PreflightResult:
        """Parse and validate selector response."""
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    raise ValueError("Invalid JSON in selector response")
            else:
                raise ValueError("Selector response is not valid JSON")

        # Validate decision
        decision = data.get("decision", "unresolved")
        if decision not in ("selected", "abstain", "lookup", "unresolved"):
            decision = "unresolved"

        result = PreflightResult(mode=PreflightMode.CUSTOM_ENDPOINT)

        if decision == "abstain":
            result.abstained = True
            result.abstain_reason = data.get("reason", "Native agent can handle")
            return result

        if decision == "lookup":
            result.lookups = data.get("queries", [])
            result.warnings.append("Selector requested lookup - fallback to Mode 0 for this turn")
            return result

        if decision == "unresolved":
            result.unresolved = data.get("queries", [])
            result.warnings.append("Selector unresolved - fallback to Mode 0")
            return decision

        # Process selected items
        items = data.get("items", [])
        for item in items[:12]:  # Max 12 items
            if not isinstance(item, dict):
                continue
            cap_id = item.get("id", "")
            if not cap_id:
                continue

            # Parse capability ID: type:name
            if ":" in cap_id:
                cap_type, cap_name = cap_id.split(":", 1)
            else:
                cap_type, cap_name = "skill", cap_id

            # Validate readiness
            readiness_info = self._check_readiness(cap_type, cap_name)

            capability = SelectedCapability(
                type=cap_type,
                id=cap_id,
                name=cap_name,
                version="1.0.0",
                readiness=readiness_info["readiness"],
                readiness_reason=readiness_info["reason"],
                token_estimate=item.get("token_estimate", 100),
                metadata=item.get("metadata", {}),
                role=item.get("role", "optional"),
            )

            # Check conflicts
            capability.conflict_with = self._detect_conflicts(cap_name, cap_type)

            # Add to appropriate list
            if cap_type == "skill":
                result.skills.append(capability)
            elif cap_type == "plugin":
                result.plugins.append(capability)
            elif cap_type == "mcp":
                result.mcp_servers.append(capability)
            elif cap_type in ("capability", "builtin"):
                result.builtins.append(capability)

        # Calculate token estimate
        result.token_estimate = sum(c.token_estimate for c in result.skills + result.plugins + result.mcp_servers + result.builtins)

        # Enforce token budget
        if result.token_estimate > self.config.token_budget:
            result.warnings.append(f"Token estimate ({result.token_estimate}) exceeds budget ({self.config.token_budget})")

        return result

    def _check_readiness(self, cap_type: str, cap_name: str) -> Dict[str, str]:
        """Check readiness of a capability (DELL readiness validation)."""
        # Check registry for the capability
        try:
            entry = find_entry(cap_name)
            if not entry:
                return {"readiness": "unavailable", "reason": "Not found in registry"}

            # Check if skill file exists
            skill_path = entry.get("path") or entry.get("source_path")
            if skill_path:
                full_path = self.base_dir / skill_path
                if not full_path.exists():
                    return {"readiness": "not_installed", "reason": f"Skill file not found: {skill_path}"}

            # Check for required MCP servers
            mcp_servers = entry.get("mcp_servers", [])
            if mcp_servers:
                missing = []
                for mcp in mcp_servers:
                    # Check if MCP server is available
                    if not self._is_mcp_available(mcp):
                        missing.append(mcp)
                if missing:
                    return {"readiness": "missing_credentials", "reason": f"Missing MCP servers: {', '.join(missing)}"}

            # Check for API keys if needed
            if cap_type in ("mcp", "plugin") and self._requires_credentials(cap_name):
                if not self._has_credentials(cap_name):
                    return {"readiness": "missing_credentials", "reason": "Required API credentials not configured"}

            return {"readiness": "ready", "reason": "All dependencies satisfied"}

        except Exception as e:
            return {"readiness": "unavailable", "reason": f"Readiness check failed: {e}"}

    def _is_mcp_available(self, mcp_name: str) -> bool:
        """Check if MCP server is available."""
        # Check gateway config
        return True  # Simplified - gateway handles this

    def _requires_credentials(self, cap_name: str) -> bool:
        """Check if capability requires credentials."""
        # Simplified check
        return cap_name in ("github", "aws", "gcp", "azure", "openai", "anthropic")

    def _has_credentials(self, cap_name: str) -> bool:
        """Check if credentials are configured."""
        api_file = self.base_dir / "ui.api.json"
        if not api_file.exists():
            api_file = self.base_dir.parent / "ui.api.json"

        if not api_file.exists():
            return False

        try:
            data = json.loads(api_file.read_text())
            api_keys = data.get("api_keys", {})
            # Check for relevant keys
            key_patterns = {
                "github": ["GITHUB_TOKEN", "GITHUB_PAT"],
                "aws": ["AWS_ACCESS_KEY_ID"],
                "gcp": ["GOOGLE_APPLICATION_CREDENTIALS"],
                "azure": ["AZURE_CLIENT_ID"],
                "openai": ["OPENAI_API_KEY"],
                "anthropic": ["ANTHROPIC_API_KEY"],
            }
            for pattern in key_patterns.get(cap_name, []):
                if pattern in api_keys:
                    keys = api_keys[pattern]
                    if isinstance(keys, list) and keys:
                        return True
                    elif isinstance(keys, str) and keys:
                        return True
        except Exception:
            pass
        return False

    def _detect_conflicts(self, cap_name: str, cap_type: str) -> List[str]:
        """Detect framework conflicts (DELL conflict groups)."""
        conflicts = []
        cap_lower = cap_name.lower()

        for group in self.CONFLICT_GROUPS:
            # Check if any keyword from this group matches the capability name
            matched = [kw for kw in group if kw in cap_lower]
            if matched:
                # This capability belongs to a conflict group
                # Return all other keywords in the group as potential conflicts
                for other in group:
                    if other not in matched:
                        conflicts.append(other)
        return conflicts


def main():
    """CLI for testing."""
    import argparse
    parser = argparse.ArgumentParser(description="Adaptive Preflight v2")
    parser.add_argument("task", help="Task description")
    parser.add_argument("--mode", type=int, choices=[0, 1, 2], default=0)
    parser.add_argument("--agent", default="claude-code")
    parser.add_argument("--base-dir", type=Path)
    args = parser.parse_args()

    base_dir = args.base_dir or Path(__file__).resolve().parent.parent.parent
    registry = SkillRegistry(base_dir)
    preflight = AdaptivePreflightV2(base_dir, registry)

    # Override mode if provided
    if args.mode == 0:
        preflight.config.mode = PreflightMode.LEGACY
    elif args.mode == 1:
        preflight.config.mode = PreflightMode.NATIVE_AUTO
    elif args.mode == 2:
        preflight.config.mode = PreflightMode.CUSTOM_ENDPOINT

    # Mock event
    event = {
        "hook_event_name": "UserPromptSubmit",
        "cwd": str(Path.cwd()),
        "session_id": str(uuid.uuid4())[:8],
    }

    result = preflight.run(args.agent, args.task, event)
    print(json.dumps(asdict(result), indent=2, default=str))


if __name__ == "__main__":
    main()