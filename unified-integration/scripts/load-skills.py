#!/usr/bin/env python3
"""
Universal Skills Loader for AI Coding Agents
Loads and matches skills from all sources based on task context
"""

import json
import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

SKILLS_DIR = Path(os.environ.get(
    "AGENT_SKILLS_DIR",
    str(Path(__file__).resolve().parent.parent / "skills"),
))

AGENT_ALIASES = {"claude": "claude-code", "claude-code": "claude-code",
                 "codex-cli": "codex", "codex": "codex", "gemini": "gemini-cli",
                 "gemini-cli": "gemini-cli", "opencode": "opencode",
                 "cursor": "cursor", "windsurf": "windsurf", "copilot": "copilot", "kiro": "kiro"}

class SkillsLoader:
    def __init__(self, agent: str = "claude-code"):
        self.agent = agent
        self.skills_index = self._load_index()

    def _load_index(self) -> Dict:
        """Load the aggregated skills index"""
        index_file = SKILLS_DIR / "all-skills.json"
        if index_file.exists():
            with open(index_file) as f:
                return json.load(f)
        return {"skills": []}

    def find_skills(self, task_description: str, max_results: int = 5) -> List[Dict]:
        """Rank relevant terms, without treating agent compatibility as relevance."""
        task_lower = task_description.casefold()
        matches = []
        stopwords = set("a an the in on is it to for of and or with this that please help me my use using create make i you can do check all analisa cek saya dan di yang untuk dengan ini nya bisa".split())
        keywords = set(re.findall(r'\b[\w+#-]+\b', task_lower)) - stopwords
        translations = {"keamanan": "security", "uji": "testing", "pengujian": "testing",
                        "perbaiki": "debugging", "arsitektur": "architecture",
                        "dokumentasi": "documentation", "tabel": "spreadsheet",
                        "presentasi": "pptx", "excel": "xlsx", "bug": "debugging"}
        keywords.update(translations[k] for k in tuple(keywords) if k in translations)
        if not keywords:
            return []

        for skill in self.skills_index.get("skills", []):
            tools = skill.get("tools") or []
            compatible = {AGENT_ALIASES[t.casefold()] for t in tools if t.casefold() in AGENT_ALIASES}
            # Some sources use tools for prerequisites (python, git, etc.),
            # or say "Agent Skills". Those are not incompatible agent names.
            if compatible and self.agent not in compatible:
                continue
            def terms(value):
                return set(re.findall(r'\b[\w+#]+\b', str(value).casefold()))
            name = str(skill.get("name", "")).casefold()
            name_terms = terms(name)
            tags = terms(" ".join(skill.get("tags") or []))
            desc = terms(skill.get("description", ""))
            when = terms(skill.get("when_to_use", ""))
            score = (12 * len(keywords & name_terms) + 5 * len(keywords & tags)
                     + 2 * len(keywords & when) + len(keywords & desc))
            if name in keywords:
                score += 30
            if score > 0:
                matches.append((score, skill))

        # Sort by score and return top matches
        matches.sort(key=lambda x: (-x[0], x[1].get("name", "")))
        return [skill for _, skill in matches[:max_results]]

    def skill_path(self, skill_name: str) -> Optional[Path]:
        """Resolve either supported layout while preventing path traversal."""
        if not skill_name or Path(skill_name).name != skill_name or skill_name in {".", ".."}:
            return None
        root = SKILLS_DIR.resolve()
        categories = SKILLS_DIR / "by-category"
        directories = sorted(categories.iterdir()) if categories.is_dir() else []
        directories.append(SKILLS_DIR / "by-agent" / self.agent)
        for directory in directories:
            for candidate in (directory / skill_name / "SKILL.md", directory / f"{skill_name}.md"):
                if candidate.is_file() and candidate.resolve().is_relative_to(root):
                    return candidate
        return None

    def load_skill(self, skill_name: str) -> Dict:
        """Load a specific skill by name.

        Supports both on-disk layouts produced by this project:
        - directory skills: by-category/<category>/<name>/SKILL.md
        - flat skills:      by-category/<category>/<name>.md
        """
        candidate = self.skill_path(skill_name)
        return self._parse_skill(candidate) if candidate else {}

    def _parse_skill(self, skill_file: Path) -> Dict:
        """Parse SKILL.md file"""
        content = skill_file.read_text()
        # Parse frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    import yaml
                    frontmatter = yaml.safe_load(parts[1])
                except ImportError:
                    print(
                        "Warning: PyYAML is not installed; returning raw skill content",
                        file=sys.stderr,
                    )
                    return {"raw": content, "file": str(skill_file)}
                body = parts[2].strip()
                return {"frontmatter": frontmatter, "body": body, "file": str(skill_file)}
        return {"raw": content, "file": str(skill_file)}


def main():
    if len(sys.argv) < 3 or not sys.argv[2:]:
        print("Usage: load-skills.py <agent> <task_description>")
        sys.exit(1)

    agent = sys.argv[1]
    task = " ".join(sys.argv[2:])

    loader = SkillsLoader(agent)
    skills = loader.find_skills(task)

    for skill in skills:
        print(f"Skill: {skill.get('name', 'Unknown')}")
        print(f"  Description: {skill.get('description', 'N/A')}")
        print(f"  Tags: {', '.join(skill.get('tags', []))}")
        print()

if __name__ == "__main__":
    main()
