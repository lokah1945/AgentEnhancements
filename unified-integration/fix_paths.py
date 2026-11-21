import json

with open('skills/all-skills.json', 'r') as f:
    data = json.load(f)

for skill in data['skills']:
    if skill['source'] == 'anthropic-skills':
        # Fix source_path to use forward slashes
        skill['source_path'] = skill['source_path'].replace('\\', '/')
        skill['path'] = skill['path'].replace('\\', '/')

with open('skills/all-skills.json', 'w') as f:
    json.dump(data, f, indent=2)
print('Fixed paths for anthropic-skills')