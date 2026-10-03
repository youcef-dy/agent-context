"""Value-silent Hindsight container, network, and auth verification."""

import json
from pathlib import Path
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler


def docker(*args):
    return subprocess.run(['docker', *args], capture_output=True, text=True,
                          check=True, timeout=12).stdout.strip()


def status(opener, url, token=None):
    headers = {'Authorization': 'Bearer ' + token} if token else {}
    try:
        with opener.open(Request(url, headers=headers), timeout=4) as response:
            response.read(128)
            return response.status
    except HTTPError as error:
        return error.code
    except (OSError, URLError):
        return 'unreachable'


def main():
    item = json.loads(docker('inspect', 'adam-hindsight'))[0]
    state = item['State']
    ip = item['NetworkSettings']['Networks']['adam-hermes-broker']['IPAddress']
    names = dict(line.split('=', 1) for line in Path('/etc/adam-hindsight.env').read_text().splitlines())
    token = names['HINDSIGHT_API_TENANT_API_KEY']
    opener = build_opener(ProxyHandler({}))
    root = 'http://' + ip + ':8888'
    print(json.dumps({
        'running': state['Running'], 'oom_killed': state['OOMKilled'],
        'exit_code': state['ExitCode'], 'restart_policy': item['HostConfig']['RestartPolicy']['Name'],
        'public_ports': any(item['NetworkSettings'].get('Ports', {}).values()),
        'health_http': status(opener, root + '/health'),
        'unauthenticated_banks_http': status(opener, root + '/v1/default/banks'),
        'authenticated_banks_http': status(opener, root + '/v1/default/banks', token),
        'memory_limit_mib': item['HostConfig']['Memory'] // 1024 ** 2,
        'stats': docker('stats', '--no-stream', '--format', '{{.MemUsage}}|{{.CPUPerc}}', 'adam-hindsight'),
    }, sort_keys=True))


if __name__ == '__main__':
    main()
