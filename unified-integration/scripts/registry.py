#!/usr/bin/env python3
"""
AgentEnhancements Skill Registry — Unified capability registry.
Aggregates skills, plugins, MCP servers, and builtins from all sources.
Enhanced with evidence-aware ranking, capability composition, and framework compatibility.
"""

import json
import os
import sys
import yaml
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib


class CapabilityRole(Enum):
    """Role of a capability in a composition."""
    PRIMARY = "primary"
    SUPPORTING = "supporting"
    OPTIONAL = "optional"
    ALTERNATIVE = "alternative"
    CONFLICT = "conflict"


class ReadinessLevel(Enum):
    """Readiness level of a capability."""
    READY = "ready"                    # Fully available, credentials installed
    GUIDE_ONLY = "guide_only"          # Documentation only, runtime not installed
    NOT_INSTALLED = "not_installed"    # Runtime not installed
    MISSING_CREDENTIALS = "missing_credentials"  # Needs API keys
    UNAVAILABLE = "unavailable"        # Cannot be used


@dataclass
class SkillEntry:
    """Unified skill entry."""
    slug: str
    category: str
    version: str
    status: str
    trigger_keywords: List[str]
    mcp_servers: List[str]
    path: str
    source: str  # skills, vendored, catalog
    content_preview: str = ""
    capabilities: List[str] = None
    framework_tags: List[str] = field(default_factory=list)  # e.g., ["django", "fastapi", "react"]
    estimated_tokens: int = 100

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.framework_tags is None:
            self.framework_tags = []


@dataclass
class PluginEntry:
    """Plugin catalog entry."""
    slug: str
    category: str
    version: str
    status: str
    trigger_keywords: List[str]
    mcp_servers: List[str]
    source_url: str
    vendored: bool
    guide_path: str
    framework_tags: List[str] = field(default_factory=list)
    readiness: str = "guide_only"


@dataclass
class RankedCapability:
    """A capability with ranking metadata."""
    entry: SkillEntry
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    readiness_score: float = 0.0
    compatibility_score: float = 0.0
    budget_score: float = 0.0
    total_score: float = 0.0
    role: CapabilityRole = CapabilityRole.OPTIONAL
    readiness: ReadinessLevel = ReadinessLevel.UNAVAILABLE
    readiness_reason: str = ""
    framework_match: bool = True


@dataclass
class CapabilityComposition:
    """Composed capability set for a task."""
    primary: List[RankedCapability] = field(default_factory=list)
    supporting: List[RankedCapability] = field(default_factory=list)
    optional: List[RankedCapability] = field(default_factory=list)
    alternatives: List[RankedCapability] = field(default_factory=list)
    conflicts: List[Tuple[RankedCapability, RankedCapability, str]] = field(default_factory=list)
    total_tokens: int = 0
    abstain_reason: str = ""


class SkillRegistry:
    """
    Unified skill registry aggregating from multiple sources:
    1. skills/ - Modular plugin tree (generated from catalog)
    2. Vendored upstream projects (anthropic-skills, agency-agents, etc.)
    3. plugin-catalog/catalog.json - Canonical plugin manifests
    4. plugin-catalog/mcp-servers.json - MCP server roadmap

    Enhanced with:
    - Evidence-aware ranking (keyword + semantic + readiness + compatibility + budget)
    - Capability composition (primary, supporting, optional, alternative, conflict)
    - Framework compatibility filtering
    - Readiness-aware scoring
    - Context budget awareness
    - Abstention logic for native agent capability
    """

    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        "django": [r"\bdjango\b", r"django-rest", r"drf\b"],
        "flask": [r"\bflask\b", r"flask-rest"],
        "fastapi": [r"\bfastapi\b", r"starlette\b"],
        "react": [r"\breact\b", r"jsx\b", r"next\.js\b", r"nextjs\b"],
        "vue": [r"\bvue\b", r"vuex\b", r"pinia\b", r"nuxt\b"],
        "angular": [r"\bangular\b", r"@angular\b", r"rxjs\b"],
        "svelte": [r"\bsvelte\b", r"sveltekit\b"],
        "express": [r"\bexpress\b", r"express\.js\b"],
        "nestjs": [r"\bnestjs\b", r"@nestjs\b"],
        "spring": [r"\bspring\b", r"spring-boot\b"],
        "rails": [r"\brails\b", r"ruby on rails\b"],
        "laravel": [r"\blaravel\b"],
        "postgresql": [r"\bpostgres(?:ql)?\b", r"psql\b"],
        "mysql": [r"\bmysql\b", r"mariadb\b"],
        "mongodb": [r"\bmongo(?:db)?\b", r"mongoose\b"],
        "redis": [r"\bredis\b"],
        "elasticsearch": [r"\belasticsearch\b", r"\bes\b"],
        "kafka": [r"\bkafka\b"],
        "rabbitmq": [r"\brabbitmq\b"],
        "docker": [r"\bdocker\b", r"dockerfile\b", r"docker-compose\b"],
        "kubernetes": [r"\bkubernetes\b", r"k8s\b", r"helm\b"],
        "aws": [r"\baws\b", r"amazon web services\b", r"lambda\b", r"dynamodb\b"],
        "gcp": [r"\bgcp\b", r"google cloud\b", r"cloud run\b", r"cloud functions\b"],
        "azure": [r"\bazure\b", r"azure functions\b"],
        "graphql": [r"\bgraphql\b", r"apollo\b", r"relay\b"],
        "grpc": [r"\bgrpc\b", r"protobuf\b"],
        "typescript": [r"\btypescript\b", r"\bts\b", r"tsx\b"],
        "python": [r"\bpython\b", r"\bpy\b", r"pip\b", r"poetry\b", r"uv\b"],
        "rust": [r"\brust\b", r"cargo\b", r"rustup\b"],
        "go": [r"\bgolang\b", r"\bgo\b", r"golang\b"],
        "testing": [r"\btest\b", r"pytest\b", r"jest\b", r"vitest\b", r"cypress\b", r"playwright\b"],
        "security": [r"\bsecurity\b", r"auth\b", r"oauth\b", r"jwt\b", r"ssl\b", r"tls\b"],
    }

    # Capability conflict groups (mutually exclusive)
    CONFLICT_GROUPS = [
        {"django", "flask", "fastapi"},  # Web frameworks
        {"react", "vue", "angular", "svelte"},  # Frontend frameworks
        {"postgresql", "mysql", "mongodb"},  # Databases
        {"aws", "gcp", "azure"},  # Cloud providers
        {"jest", "vitest", "pytest"},  # Test frameworks
    ]

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.skills_dir = base_dir / "skills"
        self.catalog_path = base_dir / "plugin-catalog" / "catalog.json"
        self.mcp_path = base_dir / "plugin-catalog" / "mcp-servers.json"
        self.vendored_dirs = [
            "anthropic-skills",
            "replica-skill",
            "agency-agents",
            "agentic-awesome-skills",
            "claude-mem",
            "headroom",
            "ponytail",
            "superpowers",
            "system-prompts-and-models-of-ai-tools",
            "task-observer",
            "ECC",
        ]

        # Caches
        self._skills_cache: Optional[Dict[str, SkillEntry]] = None
        self._plugins_cache: Optional[Dict[str, PluginEntry]] = None
        self._mcp_cache: Optional[Dict] = None
        self._catalog_cache: Optional[Dict] = None
        self._framework_cache: Optional[Dict[str, List[str]]] = None

    # =========================================================================
    # DISCOVERY
    # =========================================================================
    def discover_all_skills(self) -> Dict[str, SkillEntry]:
        """Discover skills from all sources."""
        if self._skills_cache is not None:
            return self._skills_cache

        skills = {}

        # Source 1: skills/ modular tree
        skills.update(self._discover_modular_skills())

        # Source 2: Vendored upstream projects
        skills.update(self._discover_vendored_skills())

        # Source 3: Plugin catalog (as skills)
        skills.update(self._discover_catalog_skills())

        # Deduplicate: prefer official/anthropic sources
        self._skills_cache = self._deduplicate_skills(skills)
        return self._skills_cache

    def _discover_modular_skills(self) -> Dict[str, SkillEntry]:
        """Discover skills from skills/<category>/<slug>/SKILL.md"""
        skills = {}
        if not self.skills_dir.exists():
            return skills

        for skill_file in sorted(self.skills_dir.rglob("SKILL.md")):
            try:
                skill = self._load_skill_file(skill_file, "skills")
                if skill:
                    skills[skill.slug] = skill
            except Exception as e:
                print(f"Warning: failed to load {skill_file}: {e}", file=sys.stderr)
        return skills

    def _discover_vendored_skills(self) -> Dict[str, SkillEntry]:
        """Discover skills from vendored upstream projects."""
        skills = {}
        for vendor_dir in self.vendored_dirs:
            vendor_path = self.base_dir / vendor_dir
            if not vendor_path.exists():
                continue

            for skill_file in sorted(vendor_path.rglob("SKILL.md")):
                try:
                    skill = self._load_skill_file(skill_file, f"vendored:{vendor_dir}")
                    if skill:
                        skills[skill.slug] = skill
                except Exception:
                    pass
        return skills

    def _discover_catalog_skills(self) -> Dict[str, SkillEntry]:
        """Discover skills from plugin catalog."""
        skills = {}
        if not self.catalog_path.exists():
            return skills

        try:
            catalog = json.loads(self.catalog_path.read_text())
            for slug, pdata in catalog.get("skills", {}).items():
                # Convert plugin entry to skill entry
                skill = SkillEntry(
                    slug=slug,
                    category=pdata.get("category", "uncategorized"),
                    version=pdata.get("version", "0.0.0"),
                    status=pdata.get("status", "draft"),
                    trigger_keywords=pdata.get("trigger_keywords", []),
                    mcp_servers=pdata.get("mcp_servers", []),
                    path=pdata.get("path", ""),
                    source="catalog",
                    content_preview="",
                    framework_tags=pdata.get("framework_tags", []),
                    estimated_tokens=pdata.get("estimated_tokens", 100),
                )
                skills[slug] = skill
        except Exception:
            pass
        return skills

    def _load_skill_file(self, skill_file: Path, source: str) -> Optional[SkillEntry]:
        """Load a single SKILL.md file."""
        content = skill_file.read_text(encoding="utf-8")

        # Extract YAML frontmatter
        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        fm = yaml.safe_load(parts[1])
        if not fm:
            return None

        # Extract capabilities from content
        capabilities = self._extract_capabilities(content)
        framework_tags = self._extract_framework_tags(content, fm.get("trigger_keywords", []))

        return SkillEntry(
            slug=fm.get("slug", skill_file.parent.name),
            category=fm.get("category", "uncategorized"),
            version=fm.get("version", "0.0.0"),
            status=fm.get("status", "draft"),
            trigger_keywords=fm.get("trigger_keywords", []),
            mcp_servers=fm.get("mcp_servers", []),
            path=str(skill_file.relative_to(self.base_dir)),
            source=source,
            content_preview=content[:500],
            capabilities=capabilities,
            framework_tags=framework_tags,
            estimated_tokens=fm.get("estimated_tokens", 100),
        )

    def _extract_capabilities(self, content: str) -> List[str]:
        """Extract capability bullets from skill content."""
        caps = []
        lines = content.split("\n")
        in_caps = False
        for line in lines:
            if "## Capabilities" in line or "## Capability" in line:
                in_caps = True
                continue
            if in_caps and line.startswith("## "):
                break
            if in_caps and line.strip().startswith(("- ", "1.", "2.", "3.", "4.", "5.", "6.", "7.")):
                cap = line.strip().lstrip("- 1234567. ")
                caps.append(cap)
        return caps

    def _extract_framework_tags(self, content: str, keywords: List[str]) -> List[str]:
        """Extract framework tags from content and keywords."""
        tags = set()
        text = (content + " " + " ".join(keywords)).lower()

        for framework, patterns in self.FRAMEWORK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    tags.add(framework)
                    break

        return sorted(tags)

    def _deduplicate_skills(self, skills: Dict[str, SkillEntry]) -> Dict[str, SkillEntry]:
        """Deduplicate skills preferring official sources."""
        source_priority = {
            "vendored:anthropic-skills": 1,
            "skills": 2,
            "catalog": 3,
            "vendored:replica-skill": 4,
            "vendored:agency-agents": 5,
        }

        by_slug = {}
        for skill in skills.values():
            if skill.slug not in by_slug:
                by_slug[skill.slug] = []
            by_slug[skill.slug].append(skill)

        result = {}
        for slug, candidates in by_slug.items():
            best = min(candidates, key=lambda s: source_priority.get(s.source, 99))
            result[slug] = best

        return result

    # =========================================================================
    # EVIDENCE-AWARE RANKING
    # =========================================================================
    def rank_entries(
        self,
        task: str,
        agent_type: str = "claude-code",
        stage: str = "unknown",
        role: str = "main",
        context: Optional[Dict] = None,
        token_budget: int = 400,
        max_results: int = 8,
    ) -> List[RankedCapability]:
        """
        Rank capabilities with evidence-aware scoring.

        Combines:
        - Keyword matching (exact + fuzzy)
        - Semantic relevance (capability/content matching)
        - Readiness (ready > guide_only > unavailable)
        - Framework compatibility
        - Token budget efficiency
        """
        skills = self.discover_all_skills()
        task_lower = task.lower()
        task_frameworks = self._detect_frameworks(task)

        ranked = []

        for skill in skills.values():
            # 1. Keyword score (0-1)
            keyword_score = self._score_keywords(skill, task_lower)

            # 2. Semantic score (0-1) - based on capabilities and content
            semantic_score = self._score_semantic(skill, task_lower, task_frameworks)

            # 3. Readiness score (0-1)
            readiness, readiness_reason = self._check_readiness(skill, agent_type)
            readiness_score = self._readiness_to_score(readiness)

            # 4. Compatibility score (0-1)
            compatibility_score = self._score_compatibility(skill, task_frameworks, agent_type)

            # 5. Budget score (0-1) - prefer lower token items
            budget_score = self._score_budget(skill, token_budget)

            # Weighted total (configurable weights)
            total_score = (
                keyword_score * 0.30 +
                semantic_score * 0.25 +
                readiness_score * 0.20 +
                compatibility_score * 0.15 +
                budget_score * 0.10
            )

            ranked.append(RankedCapability(
                entry=skill,
                keyword_score=keyword_score,
                semantic_score=semantic_score,
                readiness_score=readiness_score,
                compatibility_score=compatibility_score,
                budget_score=budget_score,
                total_score=total_score,
                readiness=readiness,
                readiness_reason=readiness_reason,
                framework_match=(compatibility_score > 0.5),
            ))

        # Sort by total score descending
        ranked.sort(key=lambda x: -x.total_score)

        # Apply composition logic
        composed = self._compose_capabilities(ranked[:max_results * 2], task_frameworks, token_budget)

        # Flatten and limit
        final = composed.primary + composed.supporting + composed.optional
        return final[:max_results]

    def _score_keywords(self, skill: SkillEntry, task_lower: str) -> float:
        """Score based on keyword matching."""
        if not skill.trigger_keywords:
            return 0.0

        matches = 0
        for kw in skill.trigger_keywords:
            kw_lower = kw.lower()
            if kw_lower in task_lower:
                matches += 1
            # Fuzzy: keyword parts in task
            elif any(part in task_lower for part in kw_lower.split() if len(part) > 3):
                matches += 0.5

        # Also check slug
        if skill.slug.lower() in task_lower:
            matches += 2

        # Normalize by keyword count (cap at 1.0)
        return min(matches / max(len(skill.trigger_keywords), 1) * 2, 1.0)

    def _score_semantic(self, skill: SkillEntry, task_lower: str, task_frameworks: Set[str]) -> float:
        """Score based on semantic relevance (capabilities + content)."""
        score = 0.0

        # Check capabilities
        for cap in skill.capabilities:
            cap_lower = cap.lower()
            # Simple word overlap
            task_words = set(task_lower.split())
            cap_words = set(cap_lower.split())
            overlap = len(task_words & cap_words)
            if overlap > 0:
                score += min(overlap / max(len(cap_words), 1), 1.0) * 0.5

        # Framework alignment bonus
        skill_frameworks = set(skill.framework_tags)
        if skill_frameworks & task_frameworks:
            score += 0.3

        # Content preview matching
        if skill.content_preview:
            preview_lower = skill.content_preview.lower()
            task_words = set(task_lower.split())
            preview_words = set(preview_lower.split())
            overlap = len(task_words & preview_words)
            if overlap > 2:
                score += min(overlap / 10, 0.2)

        return min(score, 1.0)

    def _check_readiness(self, skill: SkillEntry, agent_type: str) -> Tuple[ReadinessLevel, str]:
        """Check skill readiness for agent."""
        # Check if skill file exists (local skills are always ready as guides)
        path = self.base_dir / skill.path
        if path.exists():
            return ReadinessLevel.READY, "skill guide available"

        # Check if it's a catalog skill (from skills/ directory which is generated)
        if skill.source == "skills":
            # Skills from skills/ directory are generated guides - always ready
            return ReadinessLevel.READY, "skill guide available (generated)"

        # Check if it's a plugin with runtime
        plugins = self.get_plugins()
        if skill.slug in plugins:
            plugin = plugins[skill.slug]
            if plugin.status == "integrated":
                return ReadinessLevel.READY, "plugin runtime installed"
            elif plugin.status == "integrated-ready":
                return ReadinessLevel.GUIDE_ONLY, "plugin guide available; runtime must be installed separately"
            elif plugin.status == "draft":
                return ReadinessLevel.GUIDE_ONLY, "plugin guide available (draft)"

        # Catalog skills without local file are guide_only
        if skill.source == "catalog":
            return ReadinessLevel.GUIDE_ONLY, "plugin guide available"

        # Vendored skills - check if file exists in vendored dir
        if skill.source.startswith("vendored:"):
            vendored_path = self.base_dir / skill.path
            if vendored_path.exists():
                return ReadinessLevel.READY, "vendored skill guide available"
            return ReadinessLevel.GUIDE_ONLY, "vendored skill referenced but not found locally"

        return ReadinessLevel.UNAVAILABLE, "skill file not found"

    def _readiness_to_score(self, readiness: ReadinessLevel) -> float:
        """Convert readiness to score."""
        scores = {
            ReadinessLevel.READY: 1.0,
            ReadinessLevel.GUIDE_ONLY: 0.6,
            ReadinessLevel.NOT_INSTALLED: 0.3,
            ReadinessLevel.MISSING_CREDENTIALS: 0.2,
            ReadinessLevel.UNAVAILABLE: 0.0,
        }
        return scores.get(readiness, 0.0)

    def _score_compatibility(self, skill: SkillEntry, task_frameworks: Set[str], agent_type: str) -> float:
        """Score based on framework compatibility."""
        if not task_frameworks:
            return 0.5  # Neutral if no frameworks detected

        skill_frameworks = set(skill.framework_tags)
        if not skill_frameworks:
            return 0.5  # Neutral if skill has no framework tags

        # Check for conflicts
        for conflict_group in self.CONFLICT_GROUPS:
            task_in_group = task_frameworks & conflict_group
            skill_in_group = skill_frameworks & conflict_group
            if task_in_group and skill_in_group and task_in_group != skill_in_group:
                return 0.0  # Direct conflict

        # Positive match
        if skill_frameworks & task_frameworks:
            return 1.0

        # No overlap but no conflict
        return 0.3

    def _score_budget(self, skill: SkillEntry, token_budget: int) -> float:
        """Score based on token budget efficiency."""
        tokens = skill.estimated_tokens
        if tokens <= 0:
            return 0.5
        # Prefer skills that fit well in budget
        ratio = tokens / token_budget
        if ratio <= 0.25:
            return 1.0
        elif ratio <= 0.5:
            return 0.8
        elif ratio <= 0.75:
            return 0.5
        else:
            return 0.2

    def _detect_frameworks(self, task: str) -> Set[str]:
        """Detect frameworks mentioned in task."""
        task_lower = task.lower()
        frameworks = set()

        for framework, patterns in self.FRAMEWORK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, task_lower, re.IGNORECASE):
                    frameworks.add(framework)
                    break

        return frameworks

    def _compose_capabilities(
        self,
        ranked: List[RankedCapability],
        task_frameworks: Set[str],
        token_budget: int
    ) -> CapabilityComposition:
        """Compose capabilities into roles."""
        composition = CapabilityComposition()
        used_tokens = 0

        # Assign primary (top scoring, ready, compatible)
        for cap in ranked:
            if cap.total_score >= 0.6 and cap.readiness in (ReadinessLevel.READY, ReadinessLevel.GUIDE_ONLY) and cap.framework_match:
                if used_tokens + cap.entry.estimated_tokens <= token_budget:
                    cap.role = CapabilityRole.PRIMARY
                    composition.primary.append(cap)
                    used_tokens += cap.entry.estimated_tokens

        # Assign supporting (good score, ready)
        for cap in ranked:
            if cap in composition.primary:
                continue
            if cap.total_score >= 0.4 and cap.readiness in (ReadinessLevel.READY, ReadinessLevel.GUIDE_ONLY):
                if used_tokens + cap.entry.estimated_tokens <= token_budget:
                    cap.role = CapabilityRole.SUPPORTING
                    composition.supporting.append(cap)
                    used_tokens += cap.entry.estimated_tokens

        # Assign optional (lower score, or guide_only)
        for cap in ranked:
            if cap in composition.primary or cap in composition.supporting:
                continue
            if cap.total_score >= 0.2:
                if used_tokens + cap.entry.estimated_tokens <= token_budget:
                    cap.role = CapabilityRole.OPTIONAL
                    composition.optional.append(cap)
                    used_tokens += cap.entry.estimated_tokens

        # Detect alternatives (same conflict group)
        for group in self.CONFLICT_GROUPS:
            in_group = [c for c in ranked if set(c.entry.framework_tags) & group]
            if len(in_group) > 1:
                primary_in_group = [c for c in in_group if c.role == CapabilityRole.PRIMARY]
                alternatives = [c for c in in_group if c not in primary_in_group]
                for alt in alternatives:
                    alt.role = CapabilityRole.ALTERNATIVE
                    composition.alternatives.append(alt)

        # Detect conflicts
        for i, cap1 in enumerate(ranked):
            for cap2 in ranked[i+1:]:
                for group in self.CONFLICT_GROUPS:
                    if (set(cap1.entry.framework_tags) & group) and (set(cap2.entry.framework_tags) & group):
                        if cap1 != cap2:
                            conflict_tags = (set(cap1.entry.framework_tags) & group) | (set(cap2.entry.framework_tags) & group)
                            composition.conflicts.append((cap1, cap2, f"framework conflict: {', '.join(conflict_tags)}"))

        composition.total_tokens = used_tokens
        return composition

    # =========================================================================
    # ABSTENTION LOGIC
    # =========================================================================
    def should_abstain(self, task: str, agent_type: str, context: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Determine if selector should abstain (native agent can handle).

        Returns (should_abstain, reason)
        """
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

        # Check if task is just a question
        if task_lower.startswith(("what", "how", "why", "when", "where", "who")) and len(task) < 100:
            return True, "Informational query - native knowledge sufficient"

        # Check context for recent tool usage indicating simple task
        if context and context.get("recent_tools"):
            recent = context["recent_tools"][-5:]
            simple_tools = {"read_file", "write_file", "list_dir", "glob", "bash"}
            if all(t.get("tool", "") in simple_tools for t in recent):
                return True, "Recent activity uses only basic tools"

        return False, ""

    # =========================================================================
    # QUERY METHODS (Enhanced)
    # =========================================================================
    def get_skill(self, slug: str) -> Optional[SkillEntry]:
        """Get a skill by slug."""
        skills = self.discover_all_skills()
        return skills.get(slug)

    def search_skills(
        self,
        query: str,
        category: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 20
    ) -> List[SkillEntry]:
        """Search skills by keyword (legacy method, uses simple scoring)."""
        skills = self.discover_all_skills()
        query_lower = query.lower()

        results = []
        for skill in skills.values():
            if category and skill.category != category:
                continue
            if source and not skill.source.startswith(source):
                continue

            score = 0
            for kw in skill.trigger_keywords:
                if kw.lower() in query_lower:
                    score += 1
            if query_lower in skill.slug.lower():
                score += 2
            for cap in skill.capabilities:
                if query_lower in cap.lower():
                    score += 1

            if score > 0:
                results.append((score, skill))

        results.sort(key=lambda x: -x[0])
        return [s for _, s in results[:limit]]

    def map_task(self, task: str, top_n: int = 8) -> List[SkillEntry]:
        """Map a task description to top matching skills (legacy)."""
        return self.search_skills(task, limit=top_n)

    def map_task_enhanced(
        self,
        task: str,
        agent_type: str = "claude-code",
        stage: str = "unknown",
        role: str = "main",
        context: Optional[Dict] = None,
        token_budget: int = 400,
        max_results: int = 8
    ) -> CapabilityComposition:
        """Enhanced task mapping with full composition."""
        # Check abstention
        should_abstain, reason = self.should_abstain(task, agent_type, context)
        if should_abstain:
            composition = CapabilityComposition()
            composition.abstain_reason = reason
            return composition

        ranked = self.rank_entries(task, agent_type, stage, role, context, token_budget, max_results)
        composition = self._compose_capabilities(ranked, self._detect_frameworks(task), token_budget)
        return composition

    def get_skills_by_category(self, category: str) -> List[SkillEntry]:
        """Get all skills in a category."""
        skills = self.discover_all_skills()
        return [s for s in skills.values() if s.category == category]

    def get_categories(self) -> List[str]:
        """Get all categories."""
        skills = self.discover_all_skills()
        return sorted(set(s.category for s in skills.values()))

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        skills = self.discover_all_skills()
        by_category = {}
        by_source = {}
        by_status = {}

        for skill in skills.values():
            by_category[skill.category] = by_category.get(skill.category, 0) + 1
            by_source[skill.source] = by_source.get(skill.source, 0) + 1
            by_status[skill.status] = by_status.get(skill.status, 0) + 1

        return {
            "total_skills": len(skills),
            "by_category": by_category,
            "by_source": by_source,
            "by_status": by_status,
            "categories": list(by_category.keys()),
        }

    def get_catalog_summary(self) -> Dict[str, Any]:
        """Get summary for selector prompt."""
        stats = self.get_stats()
        plugins = self.get_plugins()
        mcp = self.get_mcp_servers()

        return {
            "skills": {
                "total": stats["total_skills"],
                "categories": stats["by_category"],
                "top_keywords": self._get_top_keywords(20),
            },
            "plugins": {
                "total": len(plugins),
                "by_category": self._plugin_categories(),
            },
            "mcp_servers": {
                "total": len(mcp),
                "available": sum(1 for s in mcp.values() if s.get("status") == "available"),
                "built": sum(1 for s in mcp.values() if s.get("status") == "built"),
            },
            "builtins": ["registry_search", "memory_save", "memory_load", "compression"],
        }

    def _get_top_keywords(self, limit: int) -> List[str]:
        """Get most common trigger keywords."""
        skills = self.discover_all_skills()
        kw_count = {}
        for skill in skills.values():
            for kw in skill.trigger_keywords:
                kw_count[kw] = kw_count.get(kw, 0) + 1
        return [kw for kw, _ in sorted(kw_count.items(), key=lambda x: -x[1])[:limit]]

    # =========================================================================
    # PLUGIN CATALOG
    # =========================================================================
    def get_plugins(self) -> Dict[str, PluginEntry]:
        """Get all plugin entries."""
        if self._plugins_cache is not None:
            return self._plugins_cache

        plugins = {}
        if not self.catalog_path.exists():
            self._plugins_cache = plugins
            return plugins

        try:
            catalog = json.loads(self.catalog_path.read_text())
            for slug, pdata in catalog.get("skills", {}).items():
                plugins[slug] = PluginEntry(
                    slug=slug,
                    category=pdata.get("category", "uncategorized"),
                    version=pdata.get("version", "0.0.0"),
                    status=pdata.get("status", "draft"),
                    trigger_keywords=pdata.get("trigger_keywords", []),
                    mcp_servers=pdata.get("mcp_servers", []),
                    source_url=pdata.get("source_url", ""),
                    vendored=pdata.get("vendored", False),
                    guide_path=pdata.get("path", ""),
                    framework_tags=pdata.get("framework_tags", []),
                    readiness=pdata.get("readiness", "guide_only"),
                )
        except Exception:
            pass

        self._plugins_cache = plugins
        return plugins

    def _plugin_categories(self) -> Dict[str, int]:
        plugins = self.get_plugins()
        cats = {}
        for p in plugins.values():
            cats[p.category] = cats.get(p.category, 0) + 1
        return cats

    # =========================================================================
    # MCP SERVERS
    # =========================================================================
    def get_mcp_servers(self) -> Dict[str, Dict]:
        """Get all MCP server entries."""
        if self._mcp_cache is not None:
            return self._mcp_cache

        servers = {}
        if not self.mcp_path.exists():
            self._mcp_cache = servers
            return servers

        try:
            data = json.loads(self.mcp_path.read_text())
            servers = data.get("mcp-servers", {})
            for sid, sdata in servers.items():
                sdata["id"] = sid
        except Exception:
            pass

        self._mcp_cache = servers
        return servers

    def get_mcp_server(self, server_id: str) -> Optional[Dict]:
        """Get a specific MCP server."""
        return self.get_mcp_servers().get(server_id)

    # =========================================================================
    # CATALOG REBUILD
    # =========================================================================
    def rebuild_catalog(self) -> Dict:
        """Rebuild the unified catalog (skills + plugins + MCP)."""
        self._skills_cache = None
        self._plugins_cache = None
        self._mcp_cache = None

        skills = self.discover_all_skills()
        plugins = self.get_plugins()
        mcp = self.get_mcp_servers()

        catalog = {
            "skills": {slug: asdict(s) for slug, s in skills.items()},
            "plugins": {slug: asdict(p) for slug, p in plugins.items()},
            "mcp_servers": mcp,
            "stats": self.get_stats(),
        }

        output_dir = self.base_dir / "unified-integration" / "skills"
        output_dir.mkdir(parents=True, exist_ok=True)

        (output_dir / "all-skills.json").write_text(json.dumps(catalog, indent=2))
        (output_dir / "agent-registry.json").write_text(json.dumps({
            "skills": catalog["skills"],
            "plugins": catalog["plugins"],
            "mcp_servers": catalog["mcp_servers"],
            "builtins": ["registry_search", "memory_save", "memory_load", "compression"],
        }, indent=2))

        return catalog


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Skill Registry CLI")
    parser.add_argument("command", choices=["map", "map-enhanced", "search", "show", "list", "stats", "rebuild", "categories"])
    parser.add_argument("query", nargs="?", help="Task description or search query")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--source", help="Filter by source")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--format", choices=["json", "text"], default="text")
    parser.add_argument("--base-dir", help="Base directory (default: auto-detect repo root)")
    parser.add_argument("--agent", default="claude-code", help="Agent type for enhanced mapping")
    parser.add_argument("--stage", default="unknown", help="Task stage")
    parser.add_argument("--role", default="main", help="Agent role")
    parser.add_argument("--budget", type=int, default=400, help="Token budget")

    args = parser.parse_args()

    if args.base_dir:
        base_dir = Path(args.base_dir)
    else:
        base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    if args.command == "rebuild":
        catalog = registry.rebuild_catalog()
        print(f"Catalog rebuilt: {catalog['stats']['total_skills']} skills")
        return

    if args.command == "stats":
        print(json.dumps(registry.get_stats(), indent=2))
        return

    if args.command == "categories":
        print(json.dumps(registry.get_categories(), indent=2))
        return

    if args.command == "map":
        if not args.query:
            parser.error("Task description required for map")
        matches = registry.map_task(args.query, top_n=args.limit)
        if args.format == "json":
            print(json.dumps([asdict(m) for m in matches], indent=2))
        else:
            for i, m in enumerate(matches, 1):
                print(f"{i}. {m.slug} [{m.category}] ({m.source})")
                print(f"   Keywords: {', '.join(m.trigger_keywords[:5])}")
                print(f"   Path: {m.path}")
                print()

    elif args.command == "map-enhanced":
        if not args.query:
            parser.error("Task description required for map-enhanced")
        composition = registry.map_task_enhanced(
            args.query,
            agent_type=args.agent,
            stage=args.stage,
            role=args.role,
            token_budget=args.budget,
            max_results=args.limit
        )
        if args.format == "json":
            # Convert to serializable format
            result = {
                "primary": [{"slug": c.entry.slug, "score": c.total_score, "readiness": c.readiness.value, "tokens": c.entry.estimated_tokens} for c in composition.primary],
                "supporting": [{"slug": c.entry.slug, "score": c.total_score, "readiness": c.readiness.value, "tokens": c.entry.estimated_tokens} for c in composition.supporting],
                "optional": [{"slug": c.entry.slug, "score": c.total_score, "readiness": c.readiness.value, "tokens": c.entry.estimated_tokens} for c in composition.optional],
                "alternatives": [{"slug": c.entry.slug, "score": c.total_score, "readiness": c.readiness.value} for c in composition.alternatives],
                "conflicts": [[c1.entry.slug, c2.entry.slug, reason] for c1, c2, reason in composition.conflicts],
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
            if composition.alternatives:
                print("\nALTERNATIVES:")
                for c in composition.alternatives:
                    print(f"  - {c.entry.slug} [{c.entry.category}]")
            if composition.conflicts:
                print("\nCONFLICTS:")
                for c1, c2, reason in composition.conflicts:
                    print(f"  - {c1.entry.slug} vs {c2.entry.slug}: {reason}")

    elif args.command == "search":
        if not args.query:
            parser.error("Search query required")
        matches = registry.search_skills(args.query, args.category, args.source, args.limit)
        if args.format == "json":
            print(json.dumps([asdict(m) for m in matches], indent=2))
        else:
            for m in matches:
                print(f"{m.slug} [{m.category}] - {m.source}")

    elif args.command == "show":
        if not args.query:
            parser.error("Skill slug required")
        skill = registry.get_skill(args.query)
        if skill:
            print(json.dumps(asdict(skill), indent=2))
        else:
            print(f"Skill not found: {args.query}")

    elif args.command == "list":
        skills = registry.discover_all_skills()
        for skill in sorted(skills.values(), key=lambda s: s.slug):
            if args.category and skill.category != args.category:
                continue
            print(f"{skill.slug} [{skill.category}] {skill.status} - {skill.source}")


if __name__ == "__main__":
    main()