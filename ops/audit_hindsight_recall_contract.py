"""Read-only, value-silent check of the synthetic Hindsight recall contract."""

import json
from pathlib import Path
import subprocess
from urllib.request import Request, build_opener, ProxyHandler


def main():
    inspected = subprocess.run(['docker', 'inspect', 'adam-hindsight'],
                               capture_output=True, text=True, check=True, timeout=12)
    container = json.loads(inspected.stdout)[0]
    if not container['State']['Running']:
        raise RuntimeError('Hindsight is not running')
    address = container['NetworkSettings']['Networks']['adam-hermes-broker']['IPAddress']
    settings = dict(line.split('=', 1) for line in
                    Path('/etc/adam-hindsight.env').read_text().splitlines()
                    if '=' in line)
    request = Request(
        f'http://{address}:8888/v1/default/banks/adam-hindsight-smoke/memories/recall',
        data=json.dumps({'query': 'What is the synthetic project code name?',
                         'types': ['world', 'experience'], 'max_tokens': 512,
                         'budget': 'low'}).encode(),
        headers={'Authorization': 'Bearer ' + settings['HINDSIGHT_API_TENANT_API_KEY'],
                 'Content-Type': 'application/json'}, method='POST')
    with build_opener(ProxyHandler({})).open(request, timeout=120) as response:
        payload = json.load(response)
        status = response.status
    rows = payload.get('results', [])
    first = rows[0] if rows and isinstance(rows[0], dict) else {}
    print(json.dumps({'http': status, 'result_count': len(rows),
                      'top_level_fields': sorted(payload),
                      'memory_fields': sorted(first),
                      'id_present': bool(first.get('id')),
                      'mentioned_at_present': bool(first.get('mentioned_at')),
                      'occurred_start_present': bool(first.get('occurred_start'))},
                     sort_keys=True))


if __name__ == '__main__':
    main()
