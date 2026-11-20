#!/usr/bin/env python3
"""
AgentEnhancements Load Skills — Host-aware skill filtering and on-demand loading.
Filters skills by host compatibility BEFORE ranking, supports lazy loading,
and returns minimal useful set with readiness proof.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from registry import SkillRegistry, SkillEntry, ReadinessLevel, CapabilityComposition


# Host capability matrix - what each host natively supports
HOST_CAPABILITIES = {
    "claude-code": {
        "hooks": ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop", "SubagentStart", "SubagentStop"],
        "skills": True,
        "mcp": True,
        "memory": True,
        "compression": True,
        "native_tools": ["read_file", "write_file", "edit_file", "bash", "glob", "grep", "task", "todo"],
    },
    "codex": {
        "hooks": ["user_prompt_submit", "pre_tool_use", "post_tool_use", "session_start", "session_end"],
        "skills": True,
        "mcp": True,
        "memory": True,
        "compression": True,
        "native_tools": ["read", "write", "edit", "bash", "glob", "grep", "patch", "apply_patch"],
    },
    "opencode": {
        "hooks": ["pre_llm_call", "post_llm_call", "post_tool_call"],
        "skills": True,
        "mcp": True,
        "memory": True,
        "compression": True,
        "native_tools": ["read", "write", "edit", "bash", "glob", "grep"],
    },
    "hermes": {
        "hooks": ["pre_llm_call", "post_llm_call", "post_tool_call"],
        "skills": True,
        "mcp": True,
        "memory": False,
        "compression": False,
        "native_tools": [],
    },
    "cursor": {
        "hooks": [],
        "skills": True,
        "mcp": False,
        "memory": True,
        "compression": True,
        "native_tools": [],
    },
    "gemini": {
        "hooks": [],
        "skills": False,
        "mcp": False,
        "memory": True,
        "compression": True,
        "native_tools": [],
    },
    "copilot": {
        "hooks": [],
        "skills": False,
        "mcp": False,
        "memory": False,
        "compression": False,
        "native_tools": [],
    },
    "windsurf": {
        "hooks": [],
        "skills": True,
        "mcp": False,
        "memory": True,
        "compression": True,
        "native_tools": [],
    },
    "kiro": {
        "hooks": [],
        "skills": False,
        "mcp": False,
        "memory": False,
        "compression": False,
        "native_tools": [],
    },
}


# Category to host support mapping
CATEGORY_HOST_SUPPORT = {
    "code": ["claude-code", "codex", "opencode", "cursor", "windsurf"],
    "research": ["claude-code", "codex", "opencode", "cursor", "gemini"],
    "tokens-optimization": ["claude-code", "codex", "opencode"],
    "design": ["claude-code", "cursor", "windsurf"],
    "multimedia-writing": ["claude-code", "cursor", "gemini"],
    "agency": ["claude-code", "codex", "opencode", "cursor"],
}


@dataclass
class LoadedSkill:
    """A fully loaded skill with all content."""
    entry: SkillEntry
    full_content: str
    readiness: ReadinessLevel
    readiness_reason: str
    host_compatible: bool
    estimated_tokens: int


class LoadSkills:
    """
    Host-aware skill loader with on-demand loading and filtering.

    Features:
    - Filter compatibility with host BEFORE ranking
    - Read skills on-demand (lazy loading)
    - Return minimal useful set with readiness proof
    - Support stage/role hints from preflight
    - Integrate with registry enhanced ranking
    """

    def __init__(self, base_dir: Path, registry: Optional[SkillRegistry] = None):
        self.base_dir = base_dir
        self.registry = registry or SkillRegistry(base_dir)
        self._loaded_cache: Dict[str, LoadedSkill] = {}

    def filter_by_host(self, skills: List[SkillEntry], agent_type: str) -> List[SkillEntry]:
        """Filter skills by host compatibility BEFORE ranking."""
        if agent_type not in HOST_CAPABILITIES:
            return skills  # Unknown host - allow all

        host_caps = HOST_CAPABILITIES[agent_type]
        supported_categories = set()

        # Add categories supported by this host
        for cat, hosts in CATEGORY_HOST_SUPPORT.items():
            if agent_type in hosts:
                supported_categories.add(cat)

        # Always allow builtins and core categories
        supported_categories.update(["code", "research"])  # Core categories

        filtered = []
        for skill in skills:
            # Check category support
            if skill.category in supported_categories:
                filtered.append(skill)
            # Allow skills that provide tools the host has natively
            elif any(mcp in host_caps.get("native_tools", []) for mcp in skill.mcp_servers):
                filtered.append(skill)
            # Allow skills with no specific category restriction
            elif skill.category == "uncategorized":
                filtered.append(skill)

        return filtered

    def load_on_demand(self, skill_ids: List[str], agent_type: str = "claude-code") -> List[LoadedSkill]:
        """Load full skill content on-demand for given skill IDs."""
        loaded = []

        for skill_id in skill_ids:
            if skill_id in self._loaded_cache:
                loaded.append(self._loaded_cache[skill_id])
                continue

            skill = self.registry.get_skill(skill_id)
            if not skill:
                continue

            # Read full content
            content = self._read_skill_content(skill)

            # Check readiness
            readiness, reason = self._check_readiness(skill, agent_type)

            # Check host compatibility
            host_compatible = self._is_host_compatible(skill, agent_type)

            loaded_skill = LoadedSkill(
                entry=skill,
                full_content=content,
                readiness=readiness,
                readiness_reason=reason,
                host_compatible=host_compatible,
                estimated_tokens=skill.estimated_tokens,
            )

            self._loaded_cache[skill_id] = loaded_skill
            loaded.append(loaded_skill)

        return loaded

    def _read_skill_content(self, skill: SkillEntry) -> str:
        """Read full skill file content."""
        path = self.base_dir / skill.path
        if path.exists():
            return path.read_text(encoding="utf-8")
        return f"# {skill.slug}\n\nSkill file not found at {skill.path}"

    def _check_readiness(self, skill: SkillEntry, agent_type: str) -> tuple:
        """Check skill readiness for agent."""
        path = self.base_dir / skill.path
        if path.exists():
            return ReadinessLevel.READY, "skill guide available"

        if skill.source == "skills":
            return ReadinessLevel.READY, "skill guide available (generated)"

        plugins = self.registry.get_plugins()
        if skill.slug in plugins:
            plugin = plugins[skill.slug]
            if plugin.status == "integrated":
                return ReadinessLevel.READY, "plugin runtime installed"
            elif plugin.status in ("integrated-ready", "draft"):
                return ReadinessLevel.GUIDE_ONLY, f"plugin guide available ({plugin.status})"

        if skill.source == "catalog":
            return ReadinessLevel.GUIDE_ONLY, "plugin guide available"

        if skill.source.startswith("vendored:"):
            vendored_path = self.base_dir / skill.path
            if vendored_path.exists():
                return ReadinessLevel.READY, "vendored skill guide available"
            return ReadinessLevel.GUIDE_ONLY, "vendored skill referenced but not found locally"

        return ReadinessLevel.UNAVAILABLE, "skill file not found"

    def _is_host_compatible(self, skill: SkillEntry, agent_type: str) -> bool:
        """Check if skill is compatible with host."""
        if agent_type not in HOST_CAPABILITIES:
            return True

        host_caps = HOST_CAPABILITIES[agent_type]

        # Check category support
        supported_categories = set()
        for cat, hosts in CATEGORY_HOST_SUPPORT.items():
            if agent_type in hosts:
                supported_categories.add(cat)

        if skill.category in supported_categories:
            return True

        # Check MCP server compatibility
        for mcp in skill.mcp_servers:
            if mcp in host_caps.get("native_tools", []):
                return True

        return False

    def get_minimal_set(
        self,
        task: str,
        agent_type: str = "claude-code",
        stage: str = "unknown",
        role: str = "main",
        max_tokens: int = 400,
        context: Optional[Dict] = None
    ) -> CapabilityComposition:
        """
        Get minimal useful set of skills for a task.

        Process:
        1. Filter all skills by host compatibility
        2. Use registry enhanced ranking on filtered skills
        3. Load top skills on-demand
        4. Return composition within token budget
        """
        # Get all skills
        all_skills = self.registry.discover_all_skills()
        skill_list = list(all_skills.values())

        # Filter by host FIRST
        compatible_skills = self.filter_by_host(skill_list, agent_type)

        # Create a filtered registry view for ranking
        # We'll use the registry's rank_entries but with pre-filtered skills
        ranked = self._rank_filtered_skills(
            task, compatible_skills, agent_type, stage, role, context, max_tokens
        )

        # Compose using registry logic
        task_frameworks = self.registry._detect_frameworks(task)
        composition = self.registry._compose_capabilities(ranked, task_frameworks, max_tokens)

        # Load full content for primary skills
        primary_ids = [c.entry.slug for c in composition.primary]
        supporting_ids = [c.entry.slug for c in composition.supporting]

        self.load_on_demand(primary_ids + supporting_ids, agent_type)

        return composition

    def _rank_filtered_skills(
        self,
        task: str,
        skills: List[SkillEntry],
        agent_type: str,
        stage: str,
        role: str,
        context: Optional[Dict],
        token_budget: int
    ) -> List:
        """Rank a pre-filtered list of skills."""
        # Temporarily replace registry's skill cache
        original_cache = self.registry._skills_cache
        filtered_dict = {s.slug: s for s in skills}
        self.registry._skills_cache = filtered_dict

        try:
            ranked = self.registry.rank_entries(
                task, agent_type, stage, role, context, token_budget, len(skills)
            )
        finally:
            self.registry._skills_cache = original_cache

        return ranked

    def get_skill_summary(self, skill_id: str, agent_type: str = "claude-code") -> Optional[Dict]:
        """Get a summary of a skill for quick reference."""
        loaded = self.load_on_demand([skill_id], agent_type)
        if not loaded:
            return None

        skill = loaded[0]
        return {
            "slug": skill.entry.slug,
            "category": skill.entry.category,
            "version": skill.entry.version,
            "status": skill.entry.status,
            "capabilities": skill.entry.capabilities[:5],
            "trigger_keywords": skill.entry.trigger_keywords[:5],
            "mcp_servers": skill.entry.mcp_servers,
            "readiness": skill.readiness.value,
            "readiness_reason": skill.readiness_reason,
            "host_compatible": skill.host_compatible,
            "estimated_tokens": skill.estimated_tokens,
            "framework_tags": skill.entry.framework_tags,
        }

    def get_host_compatibility_report(self, agent_type: str) -> Dict:
        """Get compatibility report for a host."""
        if agent_type not in HOST_CAPABILITIES:
            return {"error": f"Unknown host: {agent_type}"}

        all_skills = self.registry.discover_all_skills()
        host_caps = HOST_CAPABILITIES[agent_type]

        compatible = []
        incompatible = []

        for skill in all_skills.values():
            if self._is_host_compatible(skill, agent_type):
                compatible.append(skill.slug)
            else:
                incompatible.append(skill.slug)

        return {
            "agent_type": agent_type,
            "host_capabilities": host_caps,
            "compatible_count": len(compatible),
            "incompatible_count": len(incompatible),
            "compatible_categories": list(set(s.category for s in all_skills.values() if s.slug in compatible)),
            "incompatible_categories": list(set(s.category for s in all_skills.values() if s.slug in incompatible)),
        }


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Load Skills CLI")
    parser.add_argument("command", choices=["load", "minimal-set", "filter", "summary", "host-report"])
    parser.add_argument("query", nargs="?", help="Task description or skill ID")
    parser.add_argument("--agent", default="claude-code", help="Agent type")
    parser.add_argument("--stage", default="unknown", help="Task stage")
    parser.add_argument("--role", default="main", help="Agent role")
    parser.add_argument("--budget", type=int, default=400, help="Token budget")
    parser.add_argument("--skills", nargs="+", help="Skill IDs to load")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    parser.add_argument("--base-dir", help="Base directory")

    args = parser.parse_args()

    if args.base_dir:
        base_dir = Path(args.base_dir)
    else:
        base_dir = Path(__file__).parent.parent.parent

    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    if args.command == "host-report":
        if not args.query:
            # Show all hosts
            report = {}
            for host in HOST_CAPABILITIES:
                report[host] = loader.get_host_compatibility_report(host)
            print(json.dumps(report, indent=2))
        else:
            print(json.dumps(loader.get_host_compatibility_report(args.query), indent=2))
        return

    if args.command == "filter":
        if not args.query:
            parser.error("Task description required for filter")
        all_skills = list(registry.discover_all_skills().values())
        filtered = loader.filter_by_host(all_skills, args.agent)
        if args.format == "json":
            print(json.dumps([{"slug": s.slug, "category": s.category} for s in filtered], indent=2))
        else:
            for s in filtered:
                print(f"{s.slug} [{s.category}]")
        return

    if args.command == "summary":
        if not args.query:
            parser.error("Skill ID required for summary")
        summary = loader.get_skill_summary(args.query, args.agent)
        if summary:
            print(json.dumps(summary, indent=2))
        else:
            print(f"Skill not found: {args.query}")
        return

    if args.command == "load":
        if not args.skills:
            parser.error("--skills required for load")
        loaded = loader.load_on_demand(args.skills, args.agent)
        if args.format == "json":
            result = []
            for l in loaded:
                result.append({
                    "slug": l.entry.slug,
                    "readiness": l.readiness.value,
                    "readiness_reason": l.readiness_reason,
                    "host_compatible": l.host_compatible,
                    "tokens": l.estimated_tokens,
                    "content_preview": l.full_content[:200],
                })
            print(json.dumps(result, indent=2))
        else:
            for l in loaded:
                print(f"{l.entry.slug}: {l.readiness.value} ({l.readiness_reason})")
        return

    if args.command == "minimal-set":
        if not args.query:
            parser.error("Task description required for minimal-set")
        composition = loader.get_minimal_set(
            args.query,
            agent_type=args.agent,
            stage=args.stage,
            role=args.role,
            max_tokens=args.budget
        )
        if args.format == "json":
            result = {
                "primary": [{"slug": c.entry.slug, "score": c.total_score, "readiness": c.readiness.value, "tokens": c.entry.estimated_tokens} for c in composition.primary],
                "supporting": [{"slug": c.entry.slug, "score": c.total_score, "readiness": c.readiness.value, "tokens": c.entry.estimated_tokens} for c in composition.supporting],
                "optional": [{"slug": c.entry.slug, "score": c.total_score, "readiness": c.readiness.value, "tokens": c.entry.estimated_tokens} for c in composition.optional],
                "total_tokens": composition.total_tokens,
                "abstain_reason": composition.abstain_reason,
            }
            print(json.dumps(result, indent=2))
        else:
            if composition.abstain_reason:
                print(f"ABSTAIN: {composition.abstain_reason}")
                return
            print(f"Total tokens: {composition.total_tokens}/{args.budget}")
            print("\nPRIMARY:")
            for c in composition.primary:
                print(f"  - {c.entry.slug} [{c.entry.category}] score={c.total_score:.2f} readiness={c.readiness.value} tokens={c.entry.estimated_tokens}")
            print("\nSUPPORTING:")
            for c in composition.supporting:
                print(f"  - {c.entry.slug} [{c.entry.category}] score={c.total_score:.2f} readiness={c.readiness.value} tokens={c.entry.estimated_tokens}")
            print("\nOPTIONAL:")
            for c in composition.optional:
                print(f"  - {c.entry.slug} [{c.entry.category}] score={c.total_score:.2f} readiness={c.readiness.value} tokens={c.entry.estimated_tokens}")


if __name__ == "__main__":
    main()