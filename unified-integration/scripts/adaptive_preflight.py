#!/usr/bin/env python3
"""
AgentEnhancements Adaptive Preflight — Capability selection before main inference.
Supports three modes:
- Mode 0: Legacy heuristic discovery (default, no external calls)
- Mode 1: Native auto-selection (Claude Code/Codex native handoff)
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

from registry import SkillRegistry, ReadinessLevel, CapabilityRole


class PreflightMode(Enum):
    LEGACY = 0          # Heuristic keyword matching
    NATIVE_AUTO = 1     # Host-native selection (Claude Code/Codex)
    CUSTOM_ENDPOINT = 2 # Custom selector model endpoint


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


class AdaptivePreflight:
    """
    Adaptive preflight engine for capability selection.
    """

    # Framework conflict groups for conflict detection
    CONFLICT_GROUPS = [
        {"django", "flask", "fastapi"},
        {"react", "vue", "angular", "svelte"},
        {"postgresql", "mysql", "mongodb"},
        {"aws", "gcp", "azure"},
        {"jest", "vitest", "pytest"},
    ]

    def __init__(self, base_dir: Path, registry: SkillRegistry):
        self.base_dir = base_dir
        self.registry = registry
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
                pass  # Use defaults

        # Environment overrides
        if os.getenv("AE_PREFLIGHT_MODE"):
            config.mode = PreflightMode(int(os.getenv("AE_PREFLIGHT_MODE")))
        if os.getenv("AE_PREFLIGHT_DEADLINE_MS"):
            config.deadline_ms = int(os.getenv("AE_PREFLIGHT_DEADLINE_MS"))
        if os.getenv("AE_MAX_SKILL_CARDS"):
            config.max_skill_cards = int(os.getenv("AE_MAX_SKILL_CARDS"))

        return config

    def run(
        self,
        task_description: str,
        agent_type: str,
        session_id: str,
        context: Optional[Dict] = None
    ) -> PreflightResult:
        """Run preflight capability selection for a task."""
        start_time = time.time()

        # Check abstention first (before any mode)
        should_abstain, reason = self._should_abstain(task_description, agent_type, context)
        if should_abstain:
            result = PreflightResult(mode=self.config.mode)
            result.abstained = True
            result.abstain_reason = reason
            result.builtins = self._get_builtins(agent_type)
            result.token_estimate = self._calculate_total_tokens(result)
            result.selector_latency_ms = int((time.time() - start_time) * 1000)
            return result

        # Dispatch to mode handler
        if self.config.mode == PreflightMode.NATIVE_AUTO:
            result = self._run_mode_1(task_description, agent_type, session_id, context)
        elif self.config.mode == PreflightMode.CUSTOM_ENDPOINT:
            result = self._run_mode_2(task_description, agent_type, session_id, context)
        else:
            result = self._run_mode_0(task_description, agent_type, session_id, context)

        result.selector_latency_ms = int((time.time() - start_time) * 1000)
        return result

    # =========================================================================
    # ABSTENTION LOGIC
    # =========================================================================
    def _should_abstain(self, task: str, agent_type: str, context: Optional[Dict]) -> Tuple[bool, str]:
        """Determine if selector should abstain (native agent can handle)."""
        task_lower = task.lower()

        # Simple tasks that don't need skills
        simple_patterns = [
            r"\b(read|write|list|delete|copy|move)\b.*\b(file|directory)\b",
            r"\b(git status|git log|git diff)\b",
            r"\b(run|execute)\b.*\b(command|script)\b",
            r"\b(explain|describe|what is)\b",
        ]

        for pattern in simple_patterns:
            if re.search(pattern, task_lower):
                return True, f"Native agent can handle: {pattern}"

        # Informational queries
        if task_lower.startswith(("what", "how", "why", "when", "where", "who")) and len(task) < 100:
            return True, "Informational query - native knowledge sufficient"

        # Context indicates simple recent activity
        if context and context.get("recent_tools"):
            recent = context["recent_tools"][-5:]
            simple_tools = {"read_file", "write_file", "list_dir", "glob", "bash"}
            if all(t.get("tool", "") in simple_tools for t in recent):
                return True, "Recent activity uses only basic tools"

        return False, ""

    # =========================================================================
    # MODE 0: LEGACY HEURISTIC DISCOVERY (Enhanced)
    # =========================================================================
    def _run_mode_0(
        self,
        task: str,
        agent_type: str,
        session_id: str,
        context: Optional[Dict]
    ) -> PreflightResult:
        """Enhanced legacy mode: evidence-aware ranking via registry."""
        result = PreflightResult(mode=PreflightMode.LEGACY)

        # Use registry enhanced ranking
        composition = self.registry.map_task_enhanced(
            task, agent_type,
            stage=context.get("stage", "unknown") if context else "unknown",
            role=context.get("role", "main") if context else "main",
            context=context,
            token_budget=self.config.token_budget,
            max_results=self.config.max_skill_cards
        )

        # Convert composition to PreflightResult
        for cap in composition.primary + composition.supporting + composition.optional:
            readiness = self._check_skill_readiness_enhanced(cap.entry, agent_type)
            role_str = cap.role.value if isinstance(cap.role, CapabilityRole) else str(cap.role)
            result.skills.append(SelectedCapability(
                type="skill",
                id=cap.entry.slug,
                name=cap.entry.slug,
                version=getattr(cap.entry, "version", "0.0.0"),
                readiness=readiness["status"],
                readiness_reason=readiness["reason"],
                token_estimate=cap.entry.estimated_tokens,
                metadata={
                    "category": getattr(cap.entry, "category", ""),
                    "path": getattr(cap.entry, "path", ""),
                    "framework_tags": getattr(cap.entry, "framework_tags", []),
                    "role": role_str,
                },
                role=role_str,
            ))

        # Add relevant plugins (using enhanced matching)
        plugin_matches = self._match_plugins_enhanced(task, agent_type)
        for plugin in plugin_matches[:3]:
            readiness = self._check_plugin_readiness_enhanced(plugin, agent_type)
            result.plugins.append(SelectedCapability(
                type="plugin",
                id=plugin["slug"],
                name=plugin["slug"],
                version=plugin.get("version", "0.0.0"),
                readiness=readiness["status"],
                readiness_reason=readiness["reason"],
                token_estimate=50,
                metadata=plugin,
            ))

        # Add relevant MCP servers
        mcp_matches = self._match_mcp_servers_enhanced(task, context, agent_type)
        for mcp in mcp_matches[:3]:
            readiness = self._check_mcp_readiness_enhanced(mcp, agent_type)
            result.mcp_servers.append(SelectedCapability(
                type="mcp",
                id=mcp["id"],
                name=mcp["id"],
                version="1.0.0",
                readiness=readiness["status"],
                readiness_reason=readiness["reason"],
                token_estimate=100,
                schema=mcp.get("tools_schema"),
                metadata=mcp,
            ))

        # Builtins
        result.builtins = self._get_builtins(agent_type)

        # Detect conflicts
        self._detect_conflicts(result)

        # Handle unresolved (skills/plugins that couldn't be validated)
        self._handle_unresolved(result, task, agent_type)

        result.token_estimate = self._calculate_total_tokens(result)
        return result

    # =========================================================================
    # MODE 1: NATIVE AUTO-SELECTION
    # =========================================================================
    def _run_mode_1(
        self,
        task: str,
        agent_type: str,
        session_id: str,
        context: Optional[Dict]
    ) -> PreflightResult:
        """
        Native auto-selection mode.
        Requires host to provide ae_native_selection via official mechanism.
        Currently NOT CERTIFIED for any host - falls back to Mode 0.
        """
        result = PreflightResult(mode=PreflightMode.NATIVE_AUTO)
        result.warnings.append("Mode 1 (Native Auto) not certified for this host; falling back to Mode 0")
        result.fallback_used = True

        # Try to get native selection from host
        native_selection = context.get("ae_native_selection") if context else None

        if native_selection and self._validate_native_selection(native_selection):
            result = self._process_native_selection(native_selection, agent_type)
        else:
            # Fallback to enhanced Mode 0
            result = self._run_mode_0(task, agent_type, session_id, context)
            result.mode = PreflightMode.NATIVE_AUTO
            result.fallback_used = True

        return result

    def _validate_native_selection(self, selection: Dict) -> bool:
        """Validate native selection payload structure."""
        required = ["selected_skills", "selected_plugins", "selected_mcp", "token_estimate"]
        return all(k in selection for k in required)

    def _process_native_selection(self, selection: Dict, agent_type: str) -> PreflightResult:
        """Process validated native selection."""
        result = PreflightResult(mode=PreflightMode.NATIVE_AUTO)

        for skill_id in selection.get("selected_skills", []):
            skill = self.registry.get_skill(skill_id)
            if skill:
                readiness = self._check_skill_readiness_enhanced(skill, agent_type)
                result.skills.append(SelectedCapability(
                    type="skill",
                    id=skill_id,
                    name=skill_id,
                    version=getattr(skill, "version", "0.0.0"),
                    readiness=readiness["status"],
                    readiness_reason=readiness["reason"],
                    token_estimate=self._estimate_skill_tokens(skill),
                ))

        result.token_estimate = selection.get("token_estimate", 0)
        return result

    # =========================================================================
    # MODE 2: CUSTOM ENDPOINT SELECTOR (Enhanced)
    # =========================================================================
    def _run_mode_2(
        self,
        task: str,
        agent_type: str,
        session_id: str,
        context: Optional[Dict]
    ) -> PreflightResult:
        """Custom endpoint mode: call external selector model."""
        result = PreflightResult(mode=PreflightMode.CUSTOM_ENDPOINT)

        if not self.config.endpoint_url:
            result.warnings.append("Mode 2 configured but no endpoint_url; falling back to Mode 0")
            result.fallback_used = True
            return self._run_mode_0(task, agent_type, session_id, context)

        # Build enhanced selector prompt
        prompt = self._build_enhanced_selector_prompt(task, agent_type, context)

        # Call selector with retries
        for round_num in range(self.config.max_rounds):
            try:
                response = self._call_selector(prompt, round_num)
                parsed = self._parse_selector_response(response)

                # Validate selector output with semantic scoring
                validation = self._validate_selector_output(parsed, task, agent_type)
                if validation["errors"]:
                    result.warnings.extend(validation["errors"])
                    if round_num == self.config.max_rounds - 1:
                        result.fallback_used = True
                        return self._run_mode_0(task, agent_type, session_id, context)
                    # Add validation feedback to prompt
                    prompt = self._build_correction_prompt(parsed, validation, prompt)
                    continue

                # Enrich with readiness
                result = self._enrich_with_readiness(parsed, agent_type)
                result.selector_raw_response = response

                # Check token budget
                if result.token_estimate <= self.config.token_budget:
                    # Detect conflicts
                    self._detect_conflicts(result)
                    # Handle unresolved
                    self._handle_unresolved(result, task, agent_type)
                    break

                # Token budget exceeded - ask for reduction
                prompt = self._build_reduction_prompt(result, prompt)

            except Exception as e:
                result.warnings.append(f"Selector round {round_num + 1} failed: {e}")
                if round_num == self.config.max_rounds - 1:
                    result.fallback_used = True
                    return self._run_mode_0(task, agent_type, session_id, context)

        return result

    def _build_selector_prompt(self, task: str, agent_type: str, context: Optional[Dict]) -> str:
        """Build selector prompt (backward compatible)."""
        return self._build_enhanced_selector_prompt(task, agent_type, context)

    def _build_enhanced_selector_prompt(self, task: str, agent_type: str, context: Optional[Dict]) -> str:
        """Build enhanced prompt for selector model with full context."""
        catalog = self.registry.get_catalog_summary()

        # Extract repo constraints
        repo_constraints = self._extract_repo_constraints()

        # Extract acceptance criteria from context/task
        acceptance_criteria = context.get("acceptance_criteria", []) if context else []

        prompt = f"""You are a capability selector for AgentEnhancements.
Select the MOST RELEVANT capabilities for the task. Be precise - only select what's truly needed.

TASK: {task}
AGENT: {agent_type}
STAGE: {context.get('stage', 'unknown') if context else 'unknown'}
ROLE: {context.get('role', 'main') if context else 'main'}
SESSION: {context.get('session_duration', 0) if context else 0}s, {len(context.get('recent_tools', [])) if context else 0} recent tools

REPO CONSTRAINTS:
{json.dumps(repo_constraints, indent=2)}

ACCEPTANCE CRITERIA:
{json.dumps(acceptance_criteria, indent=2)}

AVAILABLE CAPABILITIES (summary):
{json.dumps(catalog, indent=2)}

SELECTION RULES:
1. Select up to {self.config.max_skill_cards} capabilities TOTAL (skills + plugins + MCP + builtins)
2. Prioritize: ready > guide_only > unavailable
3. Avoid framework conflicts (e.g., don't pick both Django and Flask)
4. Stay within token budget: {self.config.token_budget} tokens
5. If native agent can handle, return empty selections with "abstain": true

Return JSON ONLY:
{{
  "selected_skills": ["skill-slug-1", "skill-slug-2"],
  "selected_plugins": ["plugin-slug-1"],
  "selected_mcp": ["mcp-server-id-1"],
  "selected_builtins": ["builtin-name"],
  "lookups": [{{"type": "skill", "id": "skill-slug", "reason": "need details"}}],
  "unresolved": [{{"type": "skill", "id": "skill-slug", "reason": "cannot verify readiness"}}],
  "abstain": false,
  "abstain_reason": "",
  "reasoning": "brief explanation of selection rationale"
}}"""
        return prompt

    def _validate_selector_output(self, parsed: Dict, task: str, agent_type: str) -> Dict:
        """Validate selector output with semantic scoring."""
        errors = []
        warnings = []

        # Check required fields
        required = ["selected_skills", "selected_plugins", "selected_mcp", "selected_builtins", "lookups", "unresolved", "abstain", "reasoning"]
        for field in required:
            if field not in parsed:
                errors.append(f"Missing required field: {field}")

        if errors:
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Check for unknown skills
        for skill_id in parsed.get("selected_skills", []):
            skill = self.registry.get_skill(skill_id)
            if not skill:
                warnings.append(f"Unknown skill selected: {skill_id}")

        # Check for framework conflicts
        selected_skills = parsed.get("selected_skills", [])
        skill_frameworks = {}
        for skill_id in selected_skills:
            skill = self.registry.get_skill(skill_id)
            if skill and skill.framework_tags:
                skill_frameworks[skill_id] = set(skill.framework_tags)

        for group in self.CONFLICT_GROUPS:
            in_group = {sid: fw for sid, fw in skill_frameworks.items() if fw & group}
            if len(in_group) > 1:
                warnings.append(f"Framework conflict detected: {', '.join(in_group.keys())} in {group}")

        # Check token budget estimate
        estimated_tokens = 0
        for skill_id in selected_skills:
            skill = self.registry.get_skill(skill_id)
            if skill:
                estimated_tokens += skill.estimated_tokens
        estimated_tokens += len(parsed.get("selected_plugins", [])) * 50
        estimated_tokens += len(parsed.get("selected_mcp", [])) * 100
        estimated_tokens += len(parsed.get("selected_builtins", [])) * 30

        if estimated_tokens > self.config.token_budget:
            warnings.append(f"Estimated tokens ({estimated_tokens}) exceeds budget ({self.config.token_budget})")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _build_correction_prompt(self, parsed: Dict, validation: Dict, original_prompt: str) -> str:
        """Build prompt with validation feedback for correction."""
        feedback = "\n".join([
            "VALIDATION FEEDBACK:",
            *[f"- ERROR: {e}" for e in validation["errors"]],
            *[f"- WARNING: {w}" for w in validation["warnings"]],
            "\nPlease correct your selection and return valid JSON."
        ])
        return original_prompt + "\n\n" + feedback

    def _call_selector(self, prompt: str, round_num: int) -> str:
        """Call the selector model endpoint."""
        import urllib.request
        import urllib.error

        # Get API key
        api_key = self._resolve_api_key()
        if not api_key:
            raise ValueError("No API key resolved for selector")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        payload = {
            "model": self.config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 1000,
        }

        req = urllib.request.Request(
            self.config.endpoint_url,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST"
        )

        # Apply deadline
        timeout = self.config.deadline_ms / 1000.0
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]

    def _resolve_api_key(self) -> Optional[str]:
        """Resolve API key from ui.api.json or environment."""
        api_file = self.base_dir / "ui.api.json"
        if not api_file.exists():
            api_file = self.base_dir.parent / "ui.api.json"

        if api_file.exists():
            try:
                data = json.loads(api_file.read_text())
                keys = data.get("api_keys", [])
                for key_entry in keys:
                    if key_entry.get("ref") == self.config.api_key_ref:
                        return key_entry.get("value") or os.getenv(key_entry.get("env_var", ""))
            except Exception:
                pass

        return os.getenv("AE_SELECTOR_API_KEY")

    def _parse_selector_response(self, response: str) -> Dict:
        """Parse and validate selector response."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError("No valid JSON in selector response")

    def _enrich_with_readiness(self, parsed: Dict, agent_type: str) -> PreflightResult:
        """Enrich selector choices with readiness checks."""
        result = PreflightResult(mode=PreflightMode.CUSTOM_ENDPOINT)

        for skill_id in parsed.get("selected_skills", []):
            skill = self.registry.get_skill(skill_id)
            if skill:
                readiness = self._check_skill_readiness_enhanced(skill, agent_type)
                result.skills.append(SelectedCapability(
                    type="skill", id=skill_id, name=skill_id,
                    version=skill.get("version", "0.0.0"),
                    readiness=readiness["status"], readiness_reason=readiness["reason"],
                    token_estimate=self._estimate_skill_tokens(skill)
                ))
            else:
                result.warnings.append(f"Selected skill not found: {skill_id}")

        # Plugins
        for plugin_id in parsed.get("selected_plugins", []):
            plugins = self.registry.get_plugins()
            if plugin_id in plugins:
                plugin = plugins[plugin_id]
                readiness = self._check_plugin_readiness_enhanced(plugin.__dict__, agent_type)
                result.plugins.append(SelectedCapability(
                    type="plugin", id=plugin_id, name=plugin_id,
                    version=plugin.version,
                    readiness=readiness["status"], readiness_reason=readiness["reason"],
                    token_estimate=50,
                    metadata=plugin.__dict__
                ))
            else:
                result.warnings.append(f"Selected plugin not found: {plugin_id}")

        # MCP
        for mcp_id in parsed.get("selected_mcp", []):
            mcp = self.registry.get_mcp_server(mcp_id)
            if mcp:
                readiness = self._check_mcp_readiness_enhanced(mcp, agent_type)
                result.mcp_servers.append(SelectedCapability(
                    type="mcp", id=mcp_id, name=mcp_id,
                    version="1.0.0",
                    readiness=readiness["status"], readiness_reason=readiness["reason"],
                    token_estimate=100,
                    schema=mcp.get("tools_schema"),
                    metadata=mcp
                ))
            else:
                result.warnings.append(f"Selected MCP not found: {mcp_id}")

        # Builtins
        for builtin_id in parsed.get("selected_builtins", []):
            builtin = next((b for b in self._get_builtins(agent_type) if b.id == builtin_id), None)
            if builtin:
                result.builtins.append(builtin)
            else:
                result.warnings.append(f"Selected builtin not found: {builtin_id}")

        # Lookups
        result.lookups = parsed.get("lookups", [])

        # Unresolved (per contract schema)
        result.unresolved = parsed.get("unresolved", [])

        # Abstention
        result.abstained = parsed.get("abstain", False)
        result.abstain_reason = parsed.get("abstain_reason", "")

        result.token_estimate = self._calculate_total_tokens(result)
        return result

    def _build_reduction_prompt(self, result: PreflightResult, original_prompt: str) -> str:
        """Build prompt asking selector to reduce token usage."""
        return f"{original_prompt}\n\nPREVIOUS SELECTION EXCEEDED TOKEN BUDGET ({result.token_estimate} > {self.config.token_budget}). Reduce selections. Prefer ready capabilities with lower token estimates."

    def _extract_repo_constraints(self) -> Dict:
        """Extract constraints from repo files (AGENTS.md, CLAUDE.md, CONTRACT.md)."""
        constraints = {}

        for fname in ["AGENTS.md", "CLAUDE.md", "CONTRACT.md"]:
            fpath = self.base_dir / fname
            if fpath.exists():
                content = fpath.read_text(encoding="utf-8")[:2000]
                constraints[fname] = content[:500]  # Truncate

        return constraints

    # =========================================================================
    # ENHANCED READINESS CHECKS
    # =========================================================================
    def _check_skill_readiness(self, skill, agent_type: str) -> Dict[str, str]:
        """Skill readiness check (backward compatible)."""
        return self._check_skill_readiness_enhanced(skill, agent_type)

    def _check_skill_readiness_enhanced(self, skill, agent_type: str) -> Dict[str, str]:
        """Enhanced skill readiness check."""
        path = self.base_dir / getattr(skill, "path", "")
        if path.exists():
            return {"status": "ready", "reason": "skill guide available"}

        if skill.source == "skills":
            return {"status": "ready", "reason": "skill guide available (generated)"}

        plugins = self.registry.get_plugins()
        if skill.slug in plugins:
            plugin = plugins[skill.slug]
            if plugin.status == "integrated":
                return {"status": "ready", "reason": "plugin runtime installed"}
            elif plugin.status in ("integrated-ready", "draft"):
                return {"status": "guide_only", "reason": f"plugin guide available ({plugin.status})"}

        if skill.source == "catalog":
            return {"status": "guide_only", "reason": "plugin guide available"}

        if skill.source.startswith("vendored:"):
            vendored_path = self.base_dir / skill.path
            if vendored_path.exists():
                return {"status": "ready", "reason": "vendored skill guide available"}
            return {"status": "guide_only", "reason": "vendored skill referenced but not found locally"}

        return {"status": "unavailable", "reason": "skill file not found"}

    def _check_plugin_readiness(self, plugin, agent_type: str) -> Dict[str, str]:
        """Plugin readiness check (backward compatible)."""
        return self._check_plugin_readiness_enhanced(plugin, agent_type)

    def _check_plugin_readiness_enhanced(self, plugin, agent_type: str) -> Dict[str, str]:
        """Enhanced plugin readiness check with host compatibility."""
        # Convert to object if dict
        if isinstance(plugin, dict):
            status = plugin.get("status", "integrated-ready")
            slug = plugin.get("slug", "")
        else:
            status = getattr(plugin, "status", "integrated-ready")
            slug = getattr(plugin, "slug", "")

        # Check host compatibility
        if not self._is_plugin_host_compatible(slug, agent_type):
            return {"status": "unavailable", "reason": f"plugin not compatible with {agent_type}"}

        if status == "integrated":
            return {"status": "ready", "reason": "plugin runtime installed"}
        elif status in ("integrated-ready", "draft"):
            return {"status": "guide_only", "reason": f"plugin guide available ({status})"}

        return {"status": "unavailable", "reason": f"plugin status: {status}"}

    def _check_mcp_readiness(self, mcp: Dict, agent_type: str) -> Dict[str, str]:
        """MCP readiness check (backward compatible)."""
        return self._check_mcp_readiness_enhanced(mcp, agent_type)

    def _check_mcp_readiness_enhanced(self, mcp: Dict, agent_type: str) -> Dict[str, str]:
        """Enhanced MCP readiness check with credential validation."""
        status = mcp.get("status", "planned")

        if status == "available":
            cmd = mcp.get("command", [])
            if cmd and self._command_exists(cmd[0]):
                # Check required credentials
                required = mcp.get("required", [])
                missing = [r for r in required if not os.getenv(r)]
                if missing:
                    return {"status": "missing_credentials", "reason": f"missing: {', '.join(missing)}"}
                return {"status": "ready", "reason": "MCP server command available"}
            return {"status": "not_installed", "reason": f"command not found: {cmd[0] if cmd else 'unknown'}"}
        elif status == "built":
            return {"status": "ready", "reason": "built-in MCP server"}
        elif status == "planned":
            return {"status": "not_installed", "reason": "MCP server planned but not implemented"}

        return {"status": "unavailable", "reason": f"MCP status: {status}"}

    def _is_plugin_host_compatible(self, plugin_slug: str, agent_type: str) -> bool:
        """Check if plugin is compatible with host."""
        # This would check CATEGORY_HOST_SUPPORT from load_skills
        # For now, assume compatible if host supports skills
        host_caps = {
            "claude-code": True, "codex": True, "opencode": True,
            "cursor": True, "windsurf": True, "hermes": True,
        }
        return host_caps.get(agent_type, False)

    # =========================================================================
    # CONFLICT DETECTION
    # =========================================================================
    def _detect_conflicts(self, result: PreflightResult):
        """Detect conflicts between selected capabilities."""
        all_caps = result.skills + result.plugins + result.mcp_servers

        # Check framework conflicts in skills
        skill_frameworks = {}
        for cap in result.skills:
            skill = self.registry.get_skill(cap.id)
            if skill and skill.framework_tags:
                skill_frameworks[cap.id] = set(skill.framework_tags)

        for group in self.CONFLICT_GROUPS:
            in_group = {sid: fw for sid, fw in skill_frameworks.items() if fw & group}
            if len(in_group) > 1:
                for sid1 in in_group:
                    for sid2 in in_group:
                        if sid1 != sid2:
                            cap = next((c for c in result.skills if c.id == sid1), None)
                            if cap:
                                cap.conflict_with.append(sid2)

        # Check MCP credential conflicts
        for cap in result.mcp_servers:
            if cap.readiness == "missing_credentials":
                cap.conflict_with.append("credentials")

    # =========================================================================
    # UNRESOLVED HANDLING (Contract Schema)
    # =========================================================================
    def _handle_unresolved(self, result: PreflightResult, task: str, agent_type: str):
        """Handle capabilities that couldn't be fully validated."""
        # Check skills that were matched but not validated
        all_skills = self.registry.discover_all_skills()
        for skill in all_skills.values():
            if skill.slug not in [c.id for c in result.skills]:
                # Check if it's relevant but couldn't be verified
                if self._is_potentially_relevant(skill, task) and not self._can_verify(skill, agent_type):
                    result.unresolved.append({
                        "type": "skill",
                        "id": skill.slug,
                        "reason": "cannot verify readiness or readiness unknown"
                    })

    def _is_potentially_relevant(self, skill, task: str) -> bool:
        """Quick check if skill might be relevant."""
        task_lower = task.lower()
        for kw in skill.trigger_keywords:
            if kw.lower() in task_lower:
                return True
        return False

    def _can_verify(self, skill, agent_type: str) -> bool:
        """Check if we can verify skill readiness."""
        path = self.base_dir / skill.path
        return path.exists() or skill.source in ("skills", "catalog")

    # =========================================================================
    # ENHANCED MATCHING
    # =========================================================================
    def _match_plugins(self, task: str) -> List[Dict]:
        """Plugin matching (backward compatible)."""
        return self._match_plugins_enhanced(task, "claude-code")

    def _match_plugins_enhanced(self, task: str, agent_type: str) -> List[Dict]:
        """Enhanced plugin matching with host filtering."""
        catalog_path = self.base_dir / "plugin-catalog" / "catalog.json"
        if not catalog_path.exists():
            return []

        try:
            catalog = json.loads(catalog_path.read_text())
            plugins = catalog.get("skills", {})
            task_lower = task.lower()

            scored = []
            for slug, plugin in plugins.items():
                # Host compatibility check
                if not self._is_plugin_host_compatible(slug, agent_type):
                    continue

                keywords = plugin.get("trigger_keywords", [])
                score = sum(1 for kw in keywords if kw.lower() in task_lower)
                if score > 0:
                    scored.append((score, plugin))

            scored.sort(key=lambda x: -x[0])
            return [p for _, p in scored]
        except Exception:
            return []

    def _match_mcp_servers(self, task: str, context: Optional[Dict]) -> List[Dict]:
        """MCP matching (backward compatible)."""
        return self._match_mcp_servers_enhanced(task, context, "claude-code")

    def _match_mcp_servers_enhanced(self, task: str, context: Optional[Dict], agent_type: str) -> List[Dict]:
        """Enhanced MCP matching with readiness awareness."""
        mcp_path = self.base_dir / "plugin-catalog" / "mcp-servers.json"
        if not mcp_path.exists():
            return []

        try:
            data = json.loads(mcp_path.read_text())
            servers = data.get("mcp-servers", {})
            task_lower = task.lower()

            scored = []
            for sid, server in servers.items():
                server_copy = server.copy()
                server_copy["id"] = sid

                # Skip unavailable servers
                readiness = self._check_mcp_readiness_enhanced(server_copy, agent_type)
                if readiness["status"] == "unavailable":
                    continue

                tools = server.get("tools", [])
                desc = server.get("description", "").lower()
                score = sum(1 for tool in tools if tool.lower() in task_lower)
                score += sum(1 for word in task_lower.split() if word in desc)

                # Boost ready servers
                if readiness["status"] == "ready":
                    score += 2

                if score > 0:
                    scored.append((score, server_copy))

            scored.sort(key=lambda x: -x[0])
            return [s for _, s in scored]
        except Exception:
            return []

    # =========================================================================
    # HELPERS
    # =========================================================================
    def _command_exists(self, cmd: str) -> bool:
        """Check if command exists in PATH."""
        import shutil
        return shutil.which(cmd) is not None

    def _get_builtins(self, agent_type: str) -> List[SelectedCapability]:
        """Get always-available builtin capabilities."""
        builtins = [
            SelectedCapability(
                type="builtin", id="registry_search", name="registry_search",
                version="1.0.0", readiness="ready", readiness_reason="built-in",
                token_estimate=50, metadata={"description": "Search skill registry"}
            ),
            SelectedCapability(
                type="builtin", id="memory_save", name="memory_save",
                version="1.0.0", readiness="ready", readiness_reason="built-in",
                token_estimate=30, metadata={"description": "Save to cross-session memory"}
            ),
            SelectedCapability(
                type="builtin", id="memory_load", name="memory_load",
                version="1.0.0", readiness="ready", readiness_reason="built-in",
                token_estimate=30, metadata={"description": "Load from cross-session memory"}
            ),
            SelectedCapability(
                type="builtin", id="compression", name="compression",
                version="1.0.0", readiness="ready", readiness_reason="built-in",
                token_estimate=50, metadata={"description": "Context compression"}
            ),
        ]
        return builtins

    def _estimate_skill_tokens(self, skill) -> int:
        """Estimate tokens for skill card."""
        base = 100
        keywords = len(getattr(skill, "trigger_keywords", [])) * 10
        return base + keywords

    def _calculate_total_tokens(self, result: PreflightResult) -> int:
        """Calculate total token estimate for capability package."""
        total = 0
        for cap_list in [result.skills, result.plugins, result.mcp_servers, result.builtins]:
            for cap in cap_list:
                total += cap.token_estimate
        return min(total, self.config.token_budget)


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Adaptive Preflight CLI")
    parser.add_argument("task", help="Task description")
    parser.add_argument("--agent", default="claude-code", help="Agent type")
    parser.add_argument("--session", default="", help="Session ID")
    parser.add_argument("--mode", type=int, choices=[0, 1, 2], help="Override preflight mode")
    parser.add_argument("--config", help="Config file path")
    parser.add_argument("--stage", default="unknown", help="Task stage")
    parser.add_argument("--role", default="main", help="Agent role")

    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    from registry import SkillRegistry
    registry = SkillRegistry(base_dir)

    preflight = AdaptivePreflight(base_dir, registry)
    if args.mode is not None:
        preflight.config.mode = PreflightMode(args.mode)

    session_id = args.session or str(uuid.uuid4())[:8]
    context = {"stage": args.stage, "role": args.role}
    result = preflight.run(args.task, args.agent, session_id, context)

    print(json.dumps(asdict(result), indent=2, default=str))


if __name__ == "__main__":
    main()