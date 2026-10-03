"""Read-only check that the synthetic Hindsight smoke fact survived a restart."""

import json
from pathlib import Path
import subprocess
from urllib.request import Request, build_opener, ProxyHandler


def main():
    inspected = subprocess.run(
        ['docker', 'inspect', 'adam-hindsight'], capture_output=True,
        text=True, check=True, timeout=12,
    )
    container = json.loads(inspected.stdout)[0]
    if not container['State']['Running']:
        raise RuntimeError('Hindsight is not running')
    ip = container['NetworkSettings']['Networks']['adam-hermes-broker']['IPAddress']
    settings = dict(
        line.split('=', 1)
        for line in Path('/etc/adam-hindsight.env').read_text(encoding='utf-8').splitlines()
    )
    url = f'http://{ip}:8888/v1/default/banks/adam-hindsight-smoke/memories/recall'
    request = Request(url, data=json.dumps({
        'query': 'What is the synthetic project code name?',
        'types': ['world', 'experience'],
        'max_tokens': 512,
        'budget': 'low',
    }).encode(), headers={
        'Authorization': 'Bearer ' + settings['HINDSIGHT_API_TENANT_API_KEY'],
        'Content-Type': 'application/json',
    }, method='POST')
    with build_opener(ProxyHandler({})).open(request, timeout=120) as response:
        payload = json.load(response)
        status = response.status
    rows = payload.get('results', [])
    found = any('Blue Heron' in str(row.get('text', '')) for row in rows if isinstance(row, dict))
    print(json.dumps({'recall_http': status, 'recall_count': len(rows),
                      'synthetic_fact_recalled': found}))
    if status != 200 or not found:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
