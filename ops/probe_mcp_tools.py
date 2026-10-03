"""Read-only MCP diagnosis from the running Hermes container, no data output."""

import subprocess


PROBE = r'''
import asyncio, json, os
from pathlib import Path
import httpx, yaml
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

load_dotenv('/opt/data/.env', override=True)
config = yaml.safe_load(Path('/opt/data/config.yaml').read_text())

def error_kind(exc):
    if hasattr(exc, 'exceptions') and exc.exceptions:
        return [error_kind(child) for child in exc.exceptions]
    return type(exc).__name__

async def probe(name):
    entry = config['mcp_servers'][name]
    headers = {'Authorization': 'Bearer ' + os.environ['RENDER_BROKER_TOKEN']}
    stage = 'connect'
    try:
        async with httpx.AsyncClient(headers=headers, timeout=15) as client, streamable_http_client(entry['url'], http_client=client) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                stage = 'initialize'
                await session.initialize()
                stage = 'list_tools'
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                result = {'connected': True, 'tool_count': len(names)}
                if name == 'postgres' and 'context_status' in names:
                    stage = 'context_status'
                    status = await session.call_tool('context_status', {})
                    result['context_status_ok'] = not getattr(status, 'isError', getattr(status, 'is_error', False))
                    stage = 'context_search'
                    search = await session.call_tool('context_search', {'query':'synthetic-read-probe','limit':1})
                    result['context_search_ok'] = not getattr(search, 'isError', getattr(search, 'is_error', False))
                if name == 'render' and 'list_services' in names:
                    stage = 'list_services'
                    response = await session.call_tool('list_services', {'limit':1})
                    result['render_read_ok'] = not getattr(response, 'isError', getattr(response, 'is_error', False))
                return result
    except Exception as error:
        return {'connected': False, 'stage': stage, 'error_type': error_kind(error)}

async def main():
    print(json.dumps({name: await probe(name) for name in ('render', 'postgres')}))
asyncio.run(main())
'''

result = subprocess.run(
    ['docker', 'exec', '-i', 'hermes', '/opt/hermes/.venv/bin/python3', '-'],
    input=PROBE, text=True, capture_output=True, timeout=60,
)
if result.returncode:
    print('Hermes MCP probe failed: ' + (result.stderr.split(':', 1)[0] or 'unknown'))
    raise SystemExit(1)
print(result.stdout)
