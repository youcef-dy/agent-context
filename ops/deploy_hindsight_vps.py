"""One-time, guarded Hindsight API pilot deployment on Adam's VPS.

Run as root, via the reviewed SSH/VPN path. Creates only the named volume,
root-owned env file, and `adam-hindsight` container. Does not modify Hermes.
Never prints keys or database contents. Refuses to overwrite an existing setup.
"""

import os
from pathlib import Path
import secrets
import shutil
import subprocess


IMAGE = ('ghcr.io/vectorize-io/hindsight-api@'
         'sha256:1ba631f950a04460feff6b1e212bad3cdf127b0cfb3d765bdcba12f512481d7b')
ENV_PATH = Path('/etc/adam-hindsight.env')
SOURCE_ENV = Path('/srv/hermes/data/.env')
CONTAINER = 'adam-hindsight'
VOLUME = 'adam-hindsight-pg0'
PRIVATE_NETWORK = 'adam-hermes-broker'
EGRESS_NETWORK = 'adam-render-egress'


def docker(*args, check=True):
    return subprocess.run(['docker', *args], check=check, text=True,
                          capture_output=True, timeout=120)


def gemini_key():
    found = []
    for line in SOURCE_ENV.read_text(encoding='utf-8').splitlines():
        if line.startswith('GOOGLE_API_KEY='):
            found.append(line.partition('=')[2].strip().strip('"\''))
    if len(found) != 1 or not found[0] or any(char in found[0] for char in '\r\n'):
        raise RuntimeError('exactly one nonempty GOOGLE_API_KEY is required')
    return found[0]


def main():
    if os.geteuid() != 0:
        raise RuntimeError('run as root')
    if ENV_PATH.exists() or docker('inspect', CONTAINER, check=False).returncode == 0:
        raise RuntimeError('Hindsight configuration or container already exists; refusing overwrite')
    if docker('inspect', 'hermes', '--format', '{{.State.Running}}').stdout.strip() != 'true':
        raise RuntimeError('Hermes is not running')
    docker('network', 'inspect', PRIVATE_NETWORK)
    docker('network', 'inspect', EGRESS_NETWORK)
    docker('image', 'inspect', IMAGE)
    if shutil.disk_usage('/').free < 20 * 1024 ** 3:
        raise RuntimeError('less than 20 GiB disk free')
    with open('/proc/meminfo', encoding='utf-8') as stream:
        available = next(int(line.split()[1]) for line in stream if line.startswith('MemAvailable:'))
    if available < 2500 * 1024:
        raise RuntimeError('less than 2500 MiB RAM available')

    key = gemini_key()
    api_token = secrets.token_urlsafe(48)
    settings = {
        'HINDSIGHT_API_LLM_PROVIDER': 'gemini',
        'HINDSIGHT_API_LLM_API_KEY': key,
        'HINDSIGHT_API_LLM_MODEL': 'gemini-3.8-flash',
        'HINDSIGHT_API_LLM_MAX_CONCURRENT': '2',
        'HINDSIGHT_API_EMBEDDINGS_PROVIDER': 'local',
        'HINDSIGHT_API_RERANKER_PROVIDER': 'local',
        'HINDSIGHT_API_TENANT_EXTENSION': 'hindsight_api.extensions.builtin.tenant:ApiKeyTenantExtension',
        'HINDSIGHT_API_TENANT_API_KEY': api_token,
        'HINDSIGHT_API_WORKER_ID': CONTAINER,
        'HINDSIGHT_API_ACCESS_LOG': 'false',
        'HF_HUB_OFFLINE': '1',
        'TRANSFORMERS_OFFLINE': '1',
    }
    fd = os.open(ENV_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            for name, value in settings.items():
                stream.write(f'{name}={value}\n')
    except Exception:
        ENV_PATH.unlink(missing_ok=True)
        raise
    docker('volume', 'create', VOLUME)
    result = docker('run', '-d', '--name', CONTAINER, '--network', EGRESS_NETWORK,
                    '--restart', 'no', '--memory', '2250m', '--memory-swap', '2250m',
                    '--cpus', '1.0', '--pids-limit', '256', '--shm-size', '1g',
                    '--security-opt', 'no-new-privileges', '--cap-drop', 'ALL',
                    '--env-file', str(ENV_PATH),
                    '-v', f'{VOLUME}:/home/hindsight/.pg0', IMAGE)
    docker('network', 'connect', PRIVATE_NETWORK, CONTAINER)
    print('Started private Hindsight API-only container: ' + result.stdout.strip()[:12])
    print('Persistent volume: ' + VOLUME)
    print('No public ports; Hermes configuration unchanged.')


if __name__ == '__main__':
    main()
