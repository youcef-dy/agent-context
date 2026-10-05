"""Run a private, read-only owner MCP host; no migrations or provider writes."""

from __future__ import annotations

import os
from pathlib import Path
import re
import stat

from .adapters import HindsightSource, JsonHttp, LedgerSource
from .core import ContextRouter, Principal
from .mcp_server import create_app
from .postgres import PostgresLedger
from .service import OwnerContextService


def private_secret(path: str) -> str:
    selected = Path(path)
    metadata = selected.lstat()
    process_uid = os.getuid() if hasattr(os, 'getuid') else metadata.st_uid
    if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != process_uid
            or metadata.st_mode & 0o077):
        raise RuntimeError('context secret file must be owned by the service user and private')
    value = selected.read_text(encoding='utf-8').strip()
    if not value or '\n' in value or '\r' in value:
        raise RuntimeError('context secret file is invalid')
    return value


def build_service(environment: dict[str, str] | None = None) -> tuple[OwnerContextService, str, tuple[str, ...]]:
    env = environment if environment is not None else os.environ
    reader_dsn = env.get('ADAM_CONTEXT_READER_DSN', '')
    reader_dsn_file = env.get('ADAM_CONTEXT_READER_DSN_FILE', '')
    if reader_dsn and reader_dsn_file:
        raise RuntimeError('configure only one restricted PostgreSQL reader source')
    if reader_dsn_file:
        reader_dsn = private_secret(reader_dsn_file)
    if not reader_dsn:
        raise RuntimeError('restricted PostgreSQL reader DSN is required')
    token_path = env.get('ADAM_CONTEXT_MCP_TOKEN_FILE', '')
    if not token_path:
        raise RuntimeError('MCP token file path is required')
    mcp_token = private_secret(token_path)
    if not 32 <= len(mcp_token) <= 512:
        raise RuntimeError('MCP token is invalid')
    ledger = PostgresLedger(reader_dsn)
    recall = None
    hindsight_url = env.get('ADAM_CONTEXT_HINDSIGHT_URL', '')
    if hindsight_url:
        key_path = env.get('ADAM_CONTEXT_HINDSIGHT_KEY_FILE', '')
        bank = env.get('ADAM_CONTEXT_HINDSIGHT_BANK', '')
        if not key_path or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', bank):
            raise RuntimeError('Hindsight key file and fixed bank are required')
        client = JsonHttp(hindsight_url, private_secret(key_path),
                          internal_http_hosts=frozenset({'adam-hindsight'}))
        recall = HindsightSource(client, lambda _principal: bank)
    principal = Principal('adam-owner', frozenset({'owner'}), 'trusted-host-config')
    router = ContextRouter(ledger=LedgerSource(ledger), recall=recall)
    service = OwnerContextService(principal=principal, router=router, ledger=ledger)
    hosts = tuple(part.strip() for part in env.get('ADAM_CONTEXT_ALLOWED_HOSTS', '').split(',')
                  if part.strip())
    if not hosts:
        raise RuntimeError('explicit MCP host allowlist is required')
    return service, mcp_token, hosts


def main() -> None:
    import uvicorn

    service, token, hosts = build_service()
    app = create_app(service, token, allowed_hosts=hosts)
    bind = os.environ.get('ADAM_CONTEXT_BIND', '127.0.0.1')
    if bind not in {'127.0.0.1', '0.0.0.0'}:
        raise RuntimeError('unsupported context bind address')
    uvicorn.run(app, host=bind, port=8765, log_level='warning', access_log=False)


if __name__ == '__main__':
    main()
