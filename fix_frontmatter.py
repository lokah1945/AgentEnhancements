from pathlib import Path
import yaml

skills_root = Path('C:/Project/AgentEnhancements/skills')

skill_meta = {
    'karpathy-skills': {'category': 'code', 'triggers': 'minimal,first principles,vectorize,numpy,pytorch,code review,delete over refactor'},
    'mattpocock-skills': {'category': 'code', 'triggers': 'typescript,type-safe,ts-refactor,generics,type inference'},
    'agent-skills-addyosmani': {'category': 'code', 'triggers': 'frontend performance,accessibility,web vitals,core web vitals,a11y'},
    'replica-skill': {'category': 'code', 'triggers': 'reverse engineer,replica,decompile,analyze binary,app analysis'},
    'anthropic-skills': {'category': 'multimedia-writing', 'triggers': 'skill,mcp,mcp-builder,skill-creator,docx,pdf,pptx,xlsx,webapp-testing,typescript'},
    'mcp-builder': {'category': 'multimedia-writing', 'triggers': 'build an mcp server,create mcp tool,mcp integration,fastmcp,model context protocol'},
    'skill-creator': {'category': 'multimedia-writing', 'triggers': 'write a new skill,create skill,add skill,skill authoring'},
    'openmontage': {'category': 'multimedia-writing', 'triggers': 'video montage,video editing,montage,ffmpeg,video composition'},
    'hyperframes': {'category': 'multimedia-writing', 'triggers': 'talking head,avatar,heygen,elevenlabs,video generation,consent'},
    'humanizer': {'category': 'multimedia-writing', 'triggers': 'humanize text,rewrite,natural language,tone,style transfer'},
    'graphify': {'category': 'research', 'triggers': 'knowledge graph,graph,entity extraction,relationship extraction,neo4j'},
    'agent-reach': {'category': 'research', 'triggers': 'deep research,agent research,multi-source,synthesis,fact check'},
    'understand-anything': {'category': 'research', 'triggers': 'feynman,explain,teach,understand,learn,concept'},
    'rea': {'category': 'research', 'triggers': 'multi-step reasoning,reasoning,chain of thought,planning,rea'},
    'last-30-days': {'category': 'research', 'triggers': 'recent trends,last 30 days,current events,trending,news'},
    'gstack': {'category': 'tokens-optimization', 'triggers': 'token budgeting,token budget,context window,token management'},
    'caveman': {'category': 'tokens-optimization', 'triggers': 'token compression,compress context,summarize,reduce tokens'},
    'gsd': {'category': 'tokens-optimization', 'triggers': 'parallel checklist,checklist,parallel execution,task decomposition'},
    'bmad-method': {'category': 'tokens-optimization', 'triggers': 'multi-persona,persona,bmad,multi-agent,collaborative'},
    'ui-ux-pro-max': {'category': 'design', 'triggers': 'ui design tokens,design system,tokens,figma,design tokens'},
    'impeccable': {'category': 'design', 'triggers': 'visual polish,polish,refine,pixel perfect,visual quality'},
    'diagram-design': {'category': 'design', 'triggers': 'diagram,architecture diagram,flowchart,sequence diagram,mermaid'},
    'ppt-master': {'category': 'design', 'triggers': 'slide deck,presentation,powerpoint,pptx,slides'},
    'engineering': {'category': 'agency', 'triggers': 'frontend,backend,devops,engineering,software engineer,architecture'},
    'design': {'category': 'agency', 'triggers': 'ui,ux,brand,designer,user experience,interface'},
    'security': {'category': 'agency', 'triggers': 'threat model,pentest,dfir,security,vulnerability,audit'},
    'testing': {'category': 'agency', 'triggers': 'qa,e2e,performance testing,testing,test automation,playwright'},
    'nexus': {'category': 'agency', 'triggers': 'multi-agent orchestration,nexus,agent orchestration,workflow'},
}

for skill_dir in skills_root.rglob('*'):
    if skill_dir.is_dir():
        skill_file = skill_dir / 'SKILL.md'
        if skill_file.exists():
            dir_name = skill_dir.name
            if dir_name in skill_meta:
                meta = skill_meta[dir_name]
                content = skill_file.read_text(encoding='utf-8')
                if not content.startswith('---'):
                    triggers_list = ', '.join(['"' + t.strip() + '"' for t in meta['triggers'].split(',')])
                    frontmatter = f'''---
slug: {dir_name}
category: {meta['category']}
version: 0.1.0
status: draft
mcp_servers: []
trigger_keywords: [{triggers_list}]
---

'''
                    new_content = frontmatter + content
                    skill_file.write_text(new_content, encoding='utf-8')
                    print('Fixed: ' + dir_name)
                else:
                    print('Already has frontmatter: ' + dir_name)
            else:
                print('No meta for: ' + dir_name)

print('Done!')