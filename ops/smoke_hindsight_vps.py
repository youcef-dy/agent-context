"""One synthetic retain/recall test in a dedicated Hindsight smoke bank.

Writes only the literal synthetic fact below; never touches the owner bank or
Hermes. Prints statuses/counts, not memory content, credentials, or response
bodies. Re-running may add another synthetic test fact, so run once per deploy.
"""

import json
from pathlib import Path
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler


BANK = 'adam-hindsight-smoke'
FACT = 'Synthetic test only: the imaginary project code name is Blue Heron.'


def docker(*args):
    return subprocess.run(['docker', *args], capture_output=True, text=True,
                          check=True, timeout=12).stdout.strip()


def main():
    item = json.loads(docker('inspect', 'adam-hindsight'))[0]
    if not item['State']['Running']:
        raise RuntimeError('Hindsight is not running')
    ip = item['NetworkSettings']['Networks']['adam-hermes-broker']['IPAddress']
    env = dict(line.split('=', 1) for line in Path('/etc/adam-hindsight.env').read_text().splitlines())
    token = env['HINDSIGHT_API_TENANT_API_KEY']
    root = 'http://' + ip + ':8888/v1/default/banks/' + BANK
    opener = build_opener(ProxyHandler({}))

    def call(path, payload, method='POST'):
        body = json.dumps(payload).encode('utf-8')
        request = Request(root + path, data=body, method=method, headers={
            'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        try:
            with opener.open(request, timeout=120) as response:
                data = response.read(100000)
                return response.status, json.loads(data)
        except HTTPError as error:
            return error.code, {}
        except (OSError, URLError) as error:
            return type(error).__name__, {}

    created, _ = call('', {}, method='PUT')
    retained, retain_result = call('/memories', {'items': [{'content': FACT, 'context': 'synthetic deployment smoke test'}], 'async': False})
    if retained != 200:
        print(json.dumps({'bank_create_http': created, 'retain_http': retained,
                          'recall_attempted': False}))
        raise SystemExit(1)
    recalled, recall_result = call('/memories/recall', {'query': 'What is the synthetic project code name?',
                                                         'types': ['world', 'experience'],
                                                         'max_tokens': 512, 'budget': 'low'})
    rows = recall_result.get('results', []) if isinstance(recall_result, dict) else []
    found = any(isinstance(row, dict) and 'Blue Heron' in str(row.get('text', '')) for row in rows)
    print(json.dumps({'bank_create_http': created, 'retain_http': retained,
                      'retain_success': retain_result.get('success'),
                      'recall_http': recalled, 'recall_count': len(rows),
                      'synthetic_fact_recalled': found}))
    if recalled != 200 or not found:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
