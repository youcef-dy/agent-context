import hashlib
import unittest
from unittest.mock import MagicMock

from context_runtime.adapters import DocumentManifest, HindsightSource, JsonHttp, OpenVikingSource
from context_runtime.core import ContextAccessError, ContextRequest, ContextRouter, ContextSourceError, Principal
from context_runtime.identity import IdentityDirectory
from context_runtime.lineage import ArtifactRef, Dependency, affected_artifacts
from context_runtime.postgres import PostgresLedger
from context_runtime.projects import Project, ProjectCatalog
from context_runtime.test_runtime import OWNER, COMPANY, SHA, TIME, Source, evidence


class RegressionTests(unittest.TestCase):
    def test_bad_batch_does_not_leave_partial_evidence(self):
        source = Source(evidence("ledger"), evidence("ledger", recorded_at="invalid"))
        result = ContextRouter(ledger=source).retrieve(ContextRequest("x", "owner"), OWNER)
        self.assertEqual(result["items"], [])

    def test_company_query_never_calls_personal_recall(self):
        recall = Source(evidence("recall", "company:alpha"))
        result = ContextRouter(erp=Source(evidence("erp", "company:alpha")), recall=recall).retrieve(
            ContextRequest("invoice", "company:alpha"), COMPANY)
        self.assertEqual(recall.calls, 0)
        self.assertEqual(len(result["items"]), 1)

    def test_fuzzy_candidate_is_not_automatically_confirmed(self):
        catalog = ProjectCatalog([Project("travel", "Travel planning", "owner", (), "owner", TIME)])
        result = catalog.resolve("travel planing", "owner", OWNER)
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["suggested_projects"][0]["project_id"], "travel")
        self.assertIsNone(result["project_id"])

    def test_excerpt_hash_reflects_truncation_not_original(self):
        result = ContextRouter(ledger=Source(evidence("ledger", content="x" * 1000))).retrieve(
            ContextRequest("x", "owner", max_chars=500), OWNER)
        item = result["items"][0]
        self.assertEqual(item["excerpt_hash"], hashlib.sha256(("x" * 500).encode()).hexdigest())
        self.assertEqual(item["content_hash"], SHA)


class IdentityTests(unittest.TestCase):
    def test_profile_credentials_bind_distinct_principals(self):
        directory = IdentityDirectory([("a" * 40, OWNER), ("b" * 40, COMPANY)])
        self.assertIs(directory.authenticate("b" * 40), COMPANY)
        with self.assertRaises(ContextAccessError):
            directory.authenticate("c" * 40)
        with self.assertRaises(ValueError):
            IdentityDirectory([("a" * 40, OWNER), ("a" * 40, COMPANY)])


class ProviderTests(unittest.TestCase):
    def test_hindsight_bank_comes_from_host_and_timestamps_are_preserved(self):
        client = MagicMock()
        client.post.return_value = {"results": [dict(id="memory-1", text="Morning calls",
                                                   mentioned_at=TIME, occurred_start=None)]}
        adapter = HindsightSource(client, lambda actor: "owner-bank")
        rows = adapter.search(ContextRequest("calls", "owner"), OWNER)
        self.assertEqual(rows[0].canonical_id, "hindsight:owner-bank:memory-1")
        self.assertEqual(rows[0].recorded_at, "2026-09-27T10:00:00+00:00")
        self.assertEqual(client.post.call_args.args[0], "/v1/default/banks/owner-bank/memories/recall")
        self.assertEqual(adapter.search(ContextRequest("calls", "company:alpha"), COMPANY), [])

    def test_hindsight_missing_timestamp_is_not_fabricated(self):
        client = MagicMock()
        client.post.return_value = {"results": [dict(id="memory-1", text="Unknown date")]}
        with self.assertRaises(ContextSourceError):
            HindsightSource(client, lambda actor: "owner-bank").search(ContextRequest("x", "owner"), OWNER)

    def test_http_transport_cannot_call_write_or_arbitrary_routes(self):
        client = JsonHttp("https://example.invalid", "synthetic-token", transport=MagicMock())
        for path in ("/api/v1/resources", "/adam/delete", "/v1/default/banks/a/memories", "https://evil.invalid"):
            with self.assertRaises(ValueError):
                client.post(path, {})
        client.transport.open.assert_not_called()

    def test_provider_auth_headers_are_explicit(self):
        transport = MagicMock()
        response = transport.open.return_value.__enter__.return_value
        response.status = 200
        response.read.return_value = b'{"result": {"resources": []}}'
        viking = JsonHttp("https://viking.example", "synthetic-key",
                          auth_header="X-API-Key", transport=transport)
        viking.post("/api/v1/search/find", {"query": "synthetic"})
        sent = transport.open.call_args.args[0]
        self.assertEqual(sent.get_header("X-api-key"), "synthetic-key")
        self.assertIsNone(sent.get_header("Authorization"))
        with self.assertRaises(ValueError):
            JsonHttp("https://viking.example", "synthetic-key", auth_header="X-Other")

    def test_document_index_drift_is_detected_before_return(self):
        uri = "viking://resources/owner/version-1/doc.md"
        manifest = MagicMock()
        manifest.approved.return_value = DocumentManifest(
            uri, "owner", "docs:one", SHA, "1", TIME, TIME,
            indexed_text_hash=hashlib.sha256(b"original text").hexdigest())
        client = MagicMock()
        client.get.return_value = {"result": "changed indexed text"}
        adapter = OpenVikingSource(client, manifest, {"owner": "viking://resources/owner/"})
        with self.assertRaises(ContextSourceError):
            adapter.read("owner", uri, OWNER)


class PostgresTests(unittest.TestCase):
    def connection(self, role="adam_reader"):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = (role,)
        cur.description = [("memory_id",)]
        cur.fetchall.return_value = [("a" * 32,)]
        return conn, cur

    def test_search_is_parameterized_and_never_commits(self):
        conn, cur = self.connection()
        query = "x'); DROP TABLE examples; --"
        result = PostgresLedger("unused", connect=lambda: conn).search(query)
        sql, args = cur.execute.call_args.args
        self.assertNotIn(query, sql)
        self.assertEqual(args, (query, 8))
        self.assertFalse(result["audit_written"])
        conn.set_session.assert_called_once_with(readonly=True)
        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()

    def test_admin_credential_is_rejected(self):
        conn, cur = self.connection("database_owner")
        with self.assertRaises(ContextSourceError):
            PostgresLedger("unused", connect=lambda: conn).search("invoice")
        self.assertEqual(cur.execute.call_count, 1)


class LineageTests(unittest.TestCase):
    def test_upstream_change_marks_only_affected_cells_and_slides(self):
        data = ArtifactRef("owner", "dataset", "v1")
        cell = ArtifactRef("owner", "model", "v2", "Sheet1!B12")
        other_cell = ArtifactRef("owner", "model", "v2", "Sheet1!C12")
        slide = ArtifactRef("owner", "slides", "v3", "slide:4/chart:1")
        other_slide = ArtifactRef("owner", "slides", "v3", "slide:5")
        links = [Dependency(data, cell), Dependency(cell, slide), Dependency(other_cell, other_slide)]
        result = affected_artifacts(data, links, OWNER)
        self.assertEqual(set(result["affected"]), {cell, slide})
        self.assertFalse(result["truncated"])

    def test_cycles_and_result_budget_terminate(self):
        a, b, c = [ArtifactRef("owner", name, "v1") for name in "abc"]
        links = [Dependency(a, b), Dependency(b, a), Dependency(b, c)]
        result = affected_artifacts(a, links, OWNER, max_results=1)
        self.assertEqual(result["affected"], [b])
        self.assertTrue(result["truncated"])

    def test_cross_scope_links_and_queries_are_rejected(self):
        a, b = ArtifactRef("owner", "a", "v1"), ArtifactRef("company:alpha", "b", "v1")
        with self.assertRaises(ValueError):
            Dependency(a, b)
        with self.assertRaises(ContextAccessError):
            affected_artifacts(a, [], COMPANY)


if __name__ == "__main__":
    unittest.main()
