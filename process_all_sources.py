import os
import yaml
import shutil
import json
from datetime import datetime, date, timezone

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

# Auto-detect project root from script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = SCRIPT_DIR  # Script is in project root
UNIFIED_DIR = os.path.join(BASE_DIR, "unified-integration")
SKILLS_DIR = os.path.join(UNIFIED_DIR, "skills")
SKILLS_META = os.path.join(SKILLS_DIR, ".skills-meta.tmp")
INDEX_FILE = os.path.join(SKILLS_DIR, "all-skills.json")

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
    tags_val = fm.get('tags', [])
    if isinstance(tags_val, list):
        skill_tags = ','.join(str(t) for t in tags_val)
    else:
        skill_tags = str(tags_val) if tags_val else ''

    tools_val = fm.get('tools', AGENT_LIST)
    if isinstance(tools_val, list):
        skill_tools = ','.join(str(t) for t in tools_val)
    else:
        skill_tools = str(tools_val) if tools_val else 'claude-code,codex,cursor,gemini-cli,opencode,copilot,windsurf,kiro,hermes'

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
        print(f"  {source_name}: NOT FOUND at {source_dir}")
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

# Clear meta file
open(SKILLS_META, 'w').close()

# Process ALL sources
sources = [
    ("agentic-awesome-skills", os.path.join(BASE_DIR, "agentic-awesome-skills/skills")),
    ("ECC", os.path.join(BASE_DIR, "ECC/skills")),
    ("Ponytail", os.path.join(BASE_DIR, "ponytail/skills")),
    ("Superpowers", os.path.join(BASE_DIR, "superpowers/skills")),
    ("replica-skill", os.path.join(BASE_DIR, "replica-skill")),
    ("anthropic-skills", os.path.join(BASE_DIR, "anthropic-skills/skills")),
    ("task-observer", os.path.join(BASE_DIR, "task-observer")),
]

total = 0
for name, path in sources:
    total += process_source(name, path)

# Process agency-agents divisions
agency_base = os.path.join(BASE_DIR, "agency-agents/skills")
if os.path.exists(agency_base):
    for div in os.listdir(agency_base):
        div_path = os.path.join(agency_base, div)
        if os.path.isdir(div_path):
            total += process_source(f"agency-agents", div_path)

print(f"\nTotal skills processed: {total}")

# Now rebuild index
print("Rebuilding index...")

def mini_frontmatter_parse(fm_lines):
    data = {}
    key = None
    mode = None
    buf = []

    def flush():
        if key is None:
            return
        if mode == 'list':
            data[key] = [b for b in buf if b]
        elif mode == 'block':
            data[key] = ' '.join(part.strip() for part in buf).strip()
        else:
            data[key] = buf[0] if buf else ''

    for raw in fm_lines:
        line = raw.rstrip('\n')
        if not line.strip():
            continue
        indented = line[:1] in (' ', '\t')
        s = line.strip()
        if mode == 'block' and indented:
            buf.append(s)
            continue
        if mode == 'list' and indented:
            if s.startswith('-'):
                buf.append(s[1:].strip().strip('"\''))
            continue
        if indented or s.startswith('#') or ':' not in s:
            continue
        flush()
        k, _, v = s.partition(':')
        key = k.strip()
        v = v.strip()
        if v in ('>', '>-', '>+', '|', '|-', '|+'):
            mode = 'block'
            buf = []
        elif v == '':
            mode = 'list'
            buf = []
        else:
            mode = 'scalar'
            buf = [v.strip('"\'')]
            flush()
    flush()
    return data

def parse_frontmatter_file(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.read().split('\n')
    except OSError:
        return {}
    if not lines or lines[0].strip() != '---':
        return {}
    fm_lines = []
    closed = False
    for line in lines[1:]:
        if line.strip() == '---':
            closed = True
            break
        fm_lines.append(line)
    if not closed:
        return {}
    try:
        data = yaml.safe_load('\n'.join(fm_lines))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return mini_frontmatter_parse(fm_lines)

with open(SKILLS_META, 'r', encoding='utf-8', errors='replace') as f:
    meta_content = f.read()

records = meta_content.split('\x1e')
skills = []
for record in records:
    if not record:
        continue
    fields = record.split('\x1f')
    if len(fields) < 8:
        continue
    skill_name, skill_category, skill_description, skill_risk, source_name, skill_tags, skill_tools, skill_md_path = fields[:8]

    fm = parse_frontmatter_file(skill_md_path)

    date_added = fm.get('date_added', datetime.now(timezone.utc).isoformat())
    if hasattr(date_added, 'isoformat'):
        date_added = date_added.isoformat()
    
    skill = {
        "name": skill_name,
        "category": skill_category,
        "description": fm.get('description', skill_description),
        "risk": fm.get('risk', skill_risk),
        "source": source_name,
        "tags": fm.get('tags', skill_tags.split(',') if skill_tags else []),
        "tools": fm.get('tools', skill_tools.split(',') if skill_tools else []),
        "path": skill_md_path.replace(BASE_DIR + '/', '').replace(BASE_DIR + '\\', '') if BASE_DIR else skill_md_path,
        "date_added": date_added,
        "author": fm.get('author', ''),
    }
    skills.append(skill)

skills.sort(key=lambda s: s['name'])

with open(INDEX_FILE, 'w', encoding='utf-8') as f:
    json.dump({"skills": skills, "count": len(skills), "generated_at": datetime.now(timezone.utc).isoformat()}, f, indent=2, ensure_ascii=False, cls=CustomEncoder)

print(f"Indexed {len(skills)} skills")