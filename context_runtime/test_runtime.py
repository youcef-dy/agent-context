import hashlib
import unittest

from context_runtime.adapters import DocumentManifest, ErpSource, LedgerSource, OpenVikingSource
from context_runtime.core import (ContextAccessError, ContextRequest, ContextRouter,
                                  ContextSourceError, Evidence, Principal)


SHA = hashlib.sha256(b"synthetic evidence").hexdigest()
TIME = "2026-09-27T10:00:00Z"
OWNER = Principal("owner-1", frozenset({"owner"}), "trusted-test-login")
COMPANY = Principal("client-1", frozenset({"company:alpha"}), "trusted-test-login")


def evidence(kind, scope="owner", **changes):
    fields = dict(kind=kind, scope=scope, canonical_id="source:1", source_uri="test:one",
                  content_hash=SHA, content="Synthetic evidence.", observed_at=TIME,
                  recorded_at=TIME, version="1")
    fields.update(changes)
    return Evidence(**fields)


class Source:
    def __init__(self, *items, error=None):
        self.items, self.error = list(items), error
        self.calls = 0

    def search(self, request, principal):
        self.calls += 1
        if self.error:
            raise self.error
        return self.items


class RouterTests(unittest.TestCase):
    def test_scope_is_from_trusted_principal(self):
        router = ContextRouter(ledger=Source(evidence("ledger")))
        with self.assertRaises(ContextAccessError):
            router.retrieve(ContextRequest("travel", "company:alpha"), OWNER)
        with self.assertRaises(ContextAccessError):
            router.retrieve(ContextRequest("travel", "owner"), COMPANY)

    def test_company_erp_failure_blocks_all_other_sources(self):
        docs = Source(evidence("document", "company:alpha"))
        router = ContextRouter(erp=Source(error=TimeoutError()), documents=docs)
        result = router.retrieve(ContextRequest("invoice", "company:alpha"), COMPANY)
        self.assertFalse(result["answerable"])
        self.assertEqual(result["items"], [])
        self.assertEqual(docs.calls, 0)

    def test_company_without_erp_is_not_answerable(self):
        result = ContextRouter().retrieve(ContextRequest("invoice", "company:alpha"), COMPANY)
        self.assertFalse(result["answerable"])

    def test_wrong_scope_from_source_fails_closed(self):
        router = ContextRouter(ledger=Source(evidence("ledger", "company:alpha")))
        with self.assertRaises(ContextAccessError):
            router.retrieve(ContextRequest("travel", "owner", purpose="memory"), OWNER)

    def test_erp_precedes_duplicate_document_and_conflicts_are_visible(self):
        erp = evidence("erp", "company:alpha")
        old = evidence("document", "company:alpha", content_hash="a" * 64,
                       content="Old summary.")
        router = ContextRouter(erp=Source(erp), documents=Source(old))
        result = router.retrieve(ContextRequest("invoice", "company:alpha"), COMPANY)
        self.assertTrue(result["answerable"])
        self.assertEqual([x["kind"] for x in result["items"]], ["erp", "document"])
        self.assertEqual(result["conflicts"], ["source:1"])
        self.assertTrue(all(x["untrusted_source_text"] for x in result["items"]))

    def test_budget_and_duplicate(self):
        item = evidence("ledger", content="x" * 700)
        router = ContextRouter(ledger=Source(item, item))
        result = router.retrieve(ContextRequest("x", "owner", max_chars=500), OWNER)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(len(result["items"][0]["content"]), 500)
        self.assertTrue(result["items"][0]["excerpt_truncated"])

    def test_invalid_timestamp_is_discarded_and_limit_rejected(self):
        result = ContextRouter(ledger=Source(evidence("ledger", recorded_at="yesterday"))).retrieve(
            ContextRequest("x", "owner"), OWNER)
        self.assertEqual(result["items"], [])
        self.assertTrue(result["warnings"])
        with self.assertRaises(ValueError):
            ContextRequest("x", "owner", limit=True)

    def test_company_memory_is_not_enabled(self):
        result = ContextRouter().retrieve(
            ContextRequest("preference", "company:alpha", purpose="memory"), COMPANY)
        self.assertFalse(result["answerable"])

    def test_no_evidence_is_not_an_answer(self):
        result = ContextRouter(ledger=Source()).retrieve(ContextRequest("missing", "owner"), OWNER)
        self.assertFalse(result["answerable"])


class AdapterTests(unittest.TestCase):
    def test_ledger_reads_owner_only_without_writing(self):
        class Core:
            def search(self, query, limit):
                return {"items": [dict(memory_id="b" * 32, source_uri="test:msg", content_hash=SHA,
                                       title="Preference", body="Morning meetings", observed_at=TIME,
                                       recorded_at=TIME, revision=2, expires_at=None)]}
        adapter = LedgerSource(Core())
        self.assertEqual(adapter.search(ContextRequest("morning", "owner"), OWNER)[0].version, "2")
        self.assertEqual(adapter.search(ContextRequest("morning", "company:alpha"), COMPANY), [])

    def test_erp_rejects_cross_company_response(self):
        class Client:
            def __init__(self, origin, token):
                self.token = token
            def post(self, path, payload):
                return {"records": [dict(company_id="beta", record_id="1", source_uri="erp:1",
                                         content_hash=SHA, summary="Wrong company", updated_at=TIME,
                                         revision="1")]}
        adapter = ErpSource("https://erp.example", lambda p: "user-bound-token", transport_factory=Client)
        with self.assertRaises(ContextAccessError):
            adapter.search(ContextRequest("invoice", "company:alpha"), COMPANY)

    def test_openviking_filters_unapproved_and_out_of_scope_hits(self):
        prefix = "viking://resources/alpha/"
        approved_uri = prefix + "approved.md"
        class Client:
            def post(self, path, payload):
                self.payload = payload
                return {"result": {"resources": [
                    {"uri": "viking://resources/beta/private.md", "level": 2, "abstract": "Private"},
                    {"uri": prefix + "not-approved.md", "level": 2, "abstract": "No approval"},
                    {"uri": approved_uri, "level": 2, "abstract": "Safe document abstract"}]}}
        class Manifest:
            def approved(self, scope, uri):
                if uri == approved_uri:
                    return DocumentManifest(uri, scope, "docs:approved-v1", SHA, "v1", TIME, TIME)
                return None
        client = Client()
        adapter = OpenVikingSource(client, Manifest(), {"company:alpha": prefix})
        result = adapter.search(ContextRequest("policy", "company:alpha"), COMPANY)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].source_uri, "docs:approved-v1")
        self.assertEqual(client.payload["context_type"], "resource")
        self.assertEqual(client.payload["level"], 2)

    def test_full_document_read_rechecks_manifest_and_budget(self):
        uri = "viking://resources/owner/approved.md"
        class Client:
            def get(self, path, params):
                self.path, self.params = path, params
                return {"result": "x" * 1000}
        class Manifest:
            enabled = True
            def approved(self, scope, selected_uri):
                if self.enabled and scope == "owner" and selected_uri == uri:
                    return DocumentManifest(uri, scope, "docs:approved", SHA, "v1", TIME, TIME,
                                            indexed_text_hash=hashlib.sha256(("x" * 1000).encode()).hexdigest())
                return None
        client, manifest = Client(), Manifest()
        adapter = OpenVikingSource(client, manifest, {"owner": "viking://resources/owner/"})
        result = adapter.read("owner", uri, OWNER, 500)
        self.assertEqual(len(result.content), 500)
        self.assertTrue(result.excerpt_truncated)
        self.assertEqual(client.params, {"uri": uri})
        manifest.enabled = False
        with self.assertRaises(ContextAccessError):
            adapter.read("owner", uri, OWNER, 500)


if __name__ == "__main__":
    unittest.main()
