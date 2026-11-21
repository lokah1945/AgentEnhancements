#!/usr/bin/env python3
"""
Update plugin manifests with appropriate mcp_servers_suggested based on mcp-servers.json mappings.
"""
import json
import os

# Load mcp-servers.json to get plugin -> MCP server mappings
with open('plugin-catalog/mcp-servers.json') as f:
    mcp_data = json.load(f)

# Build reverse mapping: plugin -> list of MCP server IDs
plugin_to_mcp = {}
for server in mcp_data['servers']:
    for plugin in server.get('for_plugins', []):
        if plugin not in plugin_to_mcp:
            plugin_to_mcp[plugin] = []
        plugin_to_mcp[plugin].append(server['id'])

# Special handling: "all" means all plugins
all_plugins_mcp = plugin_to_mcp.get('all', [])

# Load catalog to get all plugin IDs and their manifest paths
with open('plugin-catalog/catalog.json') as f:
    catalog = json.load(f)

# Map plugin ID to manifest path
plugin_manifests = {}
for skill in catalog['skills']:
    plugin_manifests[skill['id']] = skill['manifest_path']

# Plugin-specific overrides based on analysis
plugin_mcp_mapping = {
    'research-rea': ['brave-search-mcp', 'tavily-mcp', 'memory-mcp', 'task-router-mcp'],
    'tokens-caveman': ['filesystem-mcp', 'style-mcp'],
    'tokens-gstack': ['filesystem-mcp'],
    # Agency plugins - add generic useful MCPs
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

# Update each plugin manifest
updated = 0
for plugin_id, mcp_servers in plugin_mcp_mapping.items():
    manifest_path = plugin_manifests.get(plugin_id)
    if not manifest_path:
        print(f"WARNING: No manifest path for {plugin_id}")
        continue
    
    # Auto-detect project root from script location
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(SCRIPT_DIR)
    full_path = os.path.join(BASE_DIR, manifest_path)
    if not os.path.exists(full_path):
        print(f"WARNING: Manifest not found: {full_path}")
        continue
    
    with open(full_path) as f:
        manifest = json.load(f)
    
    # Update mcp_servers_suggested
    manifest['mcp_servers_suggested'] = mcp_servers
    
    with open(full_path, 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"Updated: {plugin_id} -> {mcp_servers}")
    updated += 1

print(f"\nTotal updated: {updated}")