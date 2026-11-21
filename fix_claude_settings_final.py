import json
import shutil
import time

# Read the current settings
with open(r'C:\Users\Laptop Kantor - ASUS\.claude\settings.json', 'r', encoding='utf-8') as f:
    settings = json.load(f)

# New base path
NEW_BASE = r'C:\Project\AgentEnhancements'
NEW_STATE = NEW_BASE + r'\.agentenhancements'
NEW_MEMORY = NEW_BASE + r'\.agentenhancements\memory'
NEW_API = NEW_BASE + r'\ui.api.json'
NEW_TASK_OBSERVER = NEW_BASE + r'\.agentenhancements\memory\task-observer'
NEW_HEADROOM = NEW_BASE + r'\headroom\target\release\headroom'
NEW_CACHE = NEW_BASE + r'\.agentenhancements\cache'
NEW_UV = NEW_BASE + r'\.agentenhancements\cache\uv'
NEW_PIP = NEW_BASE + r'\.agentenhancements\cache\pip'
NEW_TIKTOKEN = NEW_BASE + r'\.agentenhancements\cache\tiktoken'
NEW_HF = NEW_BASE + r'\.agentenhancements\cache\huggingface'
NEW_TORCH = NEW_BASE + r'\.agentenhancements\cache\torch'
NEW_NPM = NEW_BASE + r'\.agentenhancements\cache\npm'
NEW_CARGO = NEW_BASE + r'\.agentenhancements\cache\cargo'
NEW_CARGO_TARGET = NEW_BASE + r'\headroom\target'
NEW_PUPPETEER = NEW_BASE + r'\.agentenhancements\cache\puppeteer'
NEW_PLAYWRIGHT = NEW_BASE + r'\.agentenhancements\cache\playwright'

# Build the env command
env_parts = [
    'AGENT_ENHANCEMENTS_STATE_DIR=' + NEW_STATE,
    'AGENT_MEMORY_ROOT=' + NEW_MEMORY,
    'AGENT_ENHANCEMENTS_API_FILE=' + NEW_API,
    'TASK_OBSERVER_WORKSPACE=' + NEW_TASK_OBSERVER,
    'HEADROOM_BIN=' + NEW_HEADROOM,
    'XDG_CACHE_HOME=' + NEW_CACHE,
    'UV_CACHE_DIR=' + NEW_UV,
    'PIP_CACHE_DIR=' + NEW_PIP,
    'TIKTOKEN_CACHE_DIR=' + NEW_TIKTOKEN,
    'HF_HOME=' + NEW_HF,
    'TORCH_HOME=' + NEW_TORCH,
    'npm_config_cache=' + NEW_NPM,
    'CARGO_HOME=' + NEW_CARGO,
    'CARGO_TARGET_DIR=' + NEW_CARGO_TARGET,
    'PUPPETEER_CACHE_DIR=' + NEW_PUPPETEER,
    'PLAYWRIGHT_BROWSERS_PATH=' + NEW_PLAYWRIGHT,
    'PYTHONPYCACHEPREFIX=',
    'TMPDIR=' + NEW_CACHE + '\\tmp',
    'TMP=' + NEW_CACHE + '\\tmp',
    'TEMP=' + NEW_CACHE + '\\tmp',
]
env_cmd = 'env ' + ' '.join(["'" + p + "'" for p in env_parts])

# Clean hook entry template
clean_hook = {
    'hooks': [
        {
            'type': 'command',
            'command': env_cmd,
            'timeout': 10
        }
    ]
}

# Replace ALL hook types with clean single entries - include all found types
hook_types = [
    'SessionStart',
    'UserPromptSubmit',
    'PostToolUse',
    'PreToolUse',
    'PreCompact',
    'SessionEnd',
    'Notification',
    'Stop',
]

for hook_type in hook_types:
    if hook_type in settings['hooks']:
        settings['hooks'][hook_type] = [clean_hook]

# Write the cleaned settings
with open(r'C:\Users\Laptop Kantor - ASUS\.claude\settings.json', 'w', encoding='utf-8') as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)

print('Settings.json fully cleaned!')
for hook_type in hook_types:
    if hook_type in settings['hooks']:
        print(f'  {hook_type}: {len(settings["hooks"][hook_type])} hook(s)')