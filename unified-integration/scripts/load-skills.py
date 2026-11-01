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
from typing import List, Dict, Any

SKILLS_DIR = Path("/root/agent-enhancements/unified-integration/skills")

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
        """Find relevant skills for a task"""
        task_lower = task_description.lower()
        matches = []

        # Simple keyword matching (in production, use embeddings)
        keywords = re.findall(r'\b\w+\b', task_lower)

        for skill in self.skills_index.get("skills", []):
            score = 0
            # Check "when_to_use" keywords
            when_to_use = skill.get("when_to_use", "").lower()
            for kw in keywords:
                if kw in when_to_use:
                    score += 2
            # Check tags
            for tag in skill.get("tags", []):
                if tag.lower() in task_lower:
                    score += 3
            # Check description
            desc = skill.get("description", "").lower()
            for kw in keywords:
                if kw in desc:
                    score += 1

            # Check agent compatibility
            if self.agent in skill.get("tools", []):
                score += 5

            if score > 0:
                matches.append((score, skill))

        # Sort by score and return top matches
        matches.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in matches[:max_results]]

    def load_skill(self, skill_name: str) -> Dict:
        """Load a specific skill by name"""
        # Search in all category directories
        for cat_dir in (SKILLS_DIR / "by-category").iterdir():
            if cat_dir.is_dir():
                skill_file = cat_dir / f"{skill_name}.md"
                if skill_file.exists():
                    return self._parse_skill(skill_file)

        # Search in agent-specific directories
        agent_dir = SKILLS_DIR / "by-agent" / self.agent
        if agent_dir.exists():
            skill_file = agent_dir / f"{skill_name}.md"
            if skill_file.exists():
                return self._parse_skill(skill_file)

        return {}

    def _parse_skill(self, skill_file: Path) -> Dict:
        """Parse SKILL.md file"""
        content = skill_file.read_text()
        # Parse frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()
                return {"frontmatter": frontmatter, "body": body, "file": str(skill_file)}
        return {"raw": content, "file": str(skill_file)}


def main():
    if len(sys.argv) < 2:
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
