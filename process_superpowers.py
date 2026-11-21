import os
import yaml
import shutil

# Auto-detect project root from script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = SCRIPT_DIR  # Script is in project root
UNIFIED_DIR = os.path.join(BASE_DIR, "unified-integration")
SKILLS_DIR = os.path.join(UNIFIED_DIR, "skills")
SKILLS_META = os.path.join(SKILLS_DIR, ".skills-meta.tmp")

CATEGORIES = ["security", "architecture", "testing", "refactoring", "code-review", "documentation", "devops", "ai-ml", "productivity", "general"]
AGENT_LIST = ["claude-code", "codex", "cursor", "gemini-cli", "opencode", "copilot", "windsurf", "kiro", "hermes"]

def parse_frontmatter(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        if content.startswith('---'):
            fm_end = content.find('\n---', 4)
            if fm_end > 0:
                fm = content[4:fm_end]
                return yaml.safe_load(fm)
    except:
        pass
    return {}

def process_skill_dir(skill_dir, source_name):
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_md):
        return 0

    fm = parse_frontmatter(skill_md)
    skill_name = fm.get('name', os.path.basename(skill_dir)).replace('/', '-')
    if not skill_name or skill_name in ('.', '..'):
        return 0

    skill_category = fm.get('category', 'general')
    if skill_category not in CATEGORIES:
        skill_category = 'general'

    skill_description = fm.get('description', '')
    skill_risk = fm.get('risk', 'low')
    skill_tags = ','.join(fm.get('tags', [])) if isinstance(fm.get('tags'), list) else str(fm.get('tags', ''))
    skill_tools = ','.join(fm.get('tools', AGENT_LIST)) if isinstance(fm.get('tools'), list) else str(fm.get('tools', 'claude-code,codex,cursor,gemini-cli,opencode,copilot,windsurf,kiro,hermes'))

    target_dir = os.path.join(SKILLS_DIR, "by-category", skill_category, skill_name)
    os.makedirs(os.path.dirname(target_dir), exist_ok=True)
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    shutil.copytree(skill_dir, target_dir)

    for tool in skill_tools.split(','):
        tool = tool.strip()
        if tool in AGENT_LIST:
            agent_target_dir = os.path.join(SKILLS_DIR, "by-agent", tool, skill_name)
            os.makedirs(os.path.dirname(agent_target_dir), exist_ok=True)
            if os.path.exists(agent_target_dir):
                shutil.rmtree(agent_target_dir)
            shutil.copytree(skill_dir, agent_target_dir)

    with open(SKILLS_META, 'a', encoding='utf-8') as f:
        f.write('\x1f'.join([
            skill_name, skill_category, skill_description,
            skill_risk, source_name, skill_tags, skill_tools,
            skill_md
        ]) + '\x1e')

    return 1

def process_source(source_name, source_dir):
    if not os.path.exists(source_dir):
        return 0

    count = 0
    if os.path.exists(os.path.join(source_dir, "SKILL.md")):
        count += process_skill_dir(source_dir, source_name)

    for item in os.listdir(source_dir):
        item_path = os.path.join(source_dir, item)
        if os.path.isdir(item_path):
            count += process_skill_dir(item_path, source_name)

    print(f"  {source_name}: processed {count} skills")
    return count

sources = [
    ("Superpowers", os.path.join(BASE_DIR, "superpowers/skills")),
]

total = 0
for name, path in sources:
    total += process_source(name, path)

print(f"\nTotal: {total}")