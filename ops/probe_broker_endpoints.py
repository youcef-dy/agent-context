"""Read-only, value-silent check of Hermes-to-broker network/auth paths."""

import json
import subprocess


PROBE = r'''
import json, os
from pathlib import Path
import httpx, yaml
from dotenv import load_dotenv
load_dotenv('/opt/data/.env', override=True)
config = yaml.safe_load(Path('/opt/data/config.yaml').read_text())
report = {}
for name in ('render', 'postgres'):
    url = config.get('mcp_servers', {}).get(name, {}).get('url')
    if not url:
        report[name] = {'configured': False}
        continue
    headers = {'Authorization': 'Bearer ' + os.environ.get('RENDER_BROKER_TOKEN', '')}
    try:
        response = httpx.get(url, headers=headers, timeout=8)
        report[name] = {'configured': True, 'status': response.status_code,
                        'content_type': response.headers.get('content-type', '').split(';')[0]}
    except Exception as error:
        report[name] = {'configured': True, 'error_type': type(error).__name__}
print(json.dumps(report))
'''

result = subprocess.run(
    ['docker', 'exec', '-i', 'hermes', '/opt/hermes/.venv/bin/python3', '-'],
    input=PROBE, text=True, capture_output=True, timeout=30,
)
if result.returncode:
    print('Hermes probe failed: ' + (result.stderr.split(':', 1)[0] or 'unknown'))
    raise SystemExit(1)
print(result.stdout)
