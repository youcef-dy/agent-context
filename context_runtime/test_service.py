import asyncio
import importlib.util
import unittest

from context_runtime.core import ContextRouter, ContextSourceError
from context_runtime.mcp_server import BearerOnlyAuth, create_app
from context_runtime.service import OwnerContextService
from context_runtime.test_runtime import OWNER, COMPANY, Source, evidence


class OwnerServiceTests(unittest.TestCase):
    def test_fixed_owner_scope_and_bounded_bundle(self):
        service = OwnerContextService(
            principal=OWNER, router=ContextRouter(ledger=Source(evidence('ledger'))))
        result = service.bundle('preference', purpose='memory', limit=1, max_chars=500)
        self.assertEqual(result['items'][0]['scope'], 'owner')
        self.assertFalse(result['live_erp_checked'])
        with self.assertRaises(ValueError):
            service.bundle('invoice', purpose='business')
        with self.assertRaises(ValueError):
            OwnerContextService(principal=COMPANY, router=ContextRouter())

    def test_status_distinguishes_configured_from_connected(self):
        ledger = object()
        service = OwnerContextService(principal=OWNER,
                                      router=ContextRouter(ledger=Source()), ledger=ledger)
        status = service.status()
        self.assertEqual(status['providers']['postgres'], 'configured_not_verified')
        self.assertEqual(status['providers']['hindsight'], 'disabled')
        self.assertFalse(status['automatic_retention'])
        self.assertTrue(status['read_only'])

    def test_history_bounds_text_and_rejects_audit_write(self):
        class Ledger:
            def history(self, memory_id, limit):
                return {'scope': 'owner', 'audit_written': False,
                        'items': [{'memory_id': memory_id, 'body': 'x' * 3000,
                                   'approval_reference': 'test:approval'}]}

        service = OwnerContextService(principal=OWNER, router=ContextRouter(),
                                      ledger=Ledger())
        result = service.history('a' * 32)
        self.assertEqual(len(result['items'][0]['body']), 2000)
        self.assertTrue(result['items'][0]['body_truncated'])

        class BadLedger:
            def history(self, memory_id, limit):
                return {'scope': 'owner', 'audit_written': True, 'items': []}

        with self.assertRaises(ContextSourceError):
            OwnerContextService(principal=OWNER, router=ContextRouter(),
                                ledger=BadLedger()).history('a' * 32)

    def test_unconfigured_document_and_project_fail_closed(self):
        service = OwnerContextService(principal=OWNER, router=ContextRouter())
        self.assertEqual(service.project_resolve('unknown')['status'], 'unavailable')
        with self.assertRaises(ContextSourceError):
            service.document_read('viking://resources/owner/test.md')

    def test_metadata_budget_rejects_oversized_packet(self):
        with self.assertRaises(ContextSourceError):
            OwnerContextService._bounded({'metadata': 'x' * 24_001})


@unittest.skipUnless(importlib.util.find_spec('starlette'), 'server extra not installed')
class BearerAuthTests(unittest.TestCase):
    def request(self, headers, body=b''):
        calls = []

        async def app(scope, receive, send):
            message = await receive()
            calls.append(message.get('body'))
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'ok'})

        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}

        async def send(message):
            calls.append(message)

        scope = {'type': 'http', 'method': 'POST', 'path': '/mcp', 'headers': headers}
        asyncio.run(BearerOnlyAuth(app, 'a' * 40)(scope, receive, send))
        return calls

    def test_rejects_missing_wrong_and_browser_origin(self):
        for headers, status in (([], 401),
                                ([(b'authorization', b'Bearer wrong')], 401),
                                ([(b'authorization', b'Bearer ' + b'a' * 40),
                                  (b'origin', b'https://evil.example')], 403)):
            result = self.request(headers)
            self.assertEqual(result[0]['status'], status)
            self.assertNotIn(b'ok', result)

    def test_valid_token_replays_bounded_body(self):
        headers = [(b'authorization', b'Bearer ' + b'a' * 40)]
        result = self.request(headers, b'synthetic')
        self.assertEqual(result[0], b'synthetic')
        self.assertEqual(result[1]['status'], 200)
        oversized = self.request(headers, b'x' * 16_385)
        self.assertEqual(oversized[0]['status'], 413)


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'server extra not installed')
class McpFactoryTests(unittest.TestCase):
    def test_factory_registers_read_only_owner_tools(self):
        from starlette.testclient import TestClient

        service = OwnerContextService(principal=OWNER, router=ContextRouter())
        app = create_app(service, 'a' * 40,
                         allowed_hosts=('adam-context:8765', 'testserver'))
        with TestClient(app) as client:
            self.assertEqual(client.get('/mcp').status_code, 401)
            self.assertEqual(client.get('/mcp', headers={
                'Authorization': 'Bearer wrong'}).status_code, 401)
        with self.assertRaises(ValueError):
            create_app(service, 'a' * 40, allowed_hosts=())


if __name__ == '__main__':
    unittest.main()
