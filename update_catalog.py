#!/usr/bin/env python3
"""
Update catalog.json to match plugin manifests' mcp_servers_suggested.
"""
import json
import os

# Plugin ID to MCP servers mapping (same as before)
plugin_mcp_mapping = {
    'research-rea': ['tavily-mcp', 'memory-mcp', 'task-router-mcp'],
    'tokens-caveman': ['filesystem-mcp', 'style-mcp'],
    'tokens-gstack': ['filesystem-mcp'],
    'agency-academic': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-design': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-engineering': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-finance': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-game-development': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-gis': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-healthcare': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-marketing': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-paid-media': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-product': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-project-management': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-research': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-sales': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-security': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-spatial-computing': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-specialized': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-support': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-testing': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
    'agency-nexus': ['filesystem-mcp', 'memory-mcp', 'task-router-mcp'],
}

# Load catalog
with open('plugin-catalog/catalog.json') as f:
    catalog = json.load(f)

# Update each skill in catalog
updated = 0
for skill in catalog['skills']:
    plugin_id = skill['id']
    if plugin_id in plugin_mcp_mapping:
        skill['mcp_servers'] = plugin_mcp_mapping[plugin_id]
        print(f"Updated catalog: {plugin_id} -> {plugin_mcp_mapping[plugin_id]}")
        updated += 1

# Save catalog
with open('plugin-catalog/catalog.json', 'w') as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

print(f"\nTotal catalog entries updated: {updated}")