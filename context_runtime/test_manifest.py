import unittest
from unittest.mock import MagicMock

from context_runtime.manifest import PostgresManifestStore
from context_runtime.core import ContextSourceError


class ManifestTests(unittest.TestCase):
    def connection(self, row, role="adam_reader"):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(role,), row]
        return conn, cursor

    def test_latest_approved_version_is_returned_with_exact_uri_query(self):
        row = ("docs:policy", "v3", "a" * 64, "2026-01-01T00:00:00Z",
               "2026-01-02T00:00:00Z", None, "APPROVED", "b" * 64)
        conn, cursor = self.connection(row)
        store = PostgresManifestStore("synthetic", connect=lambda: conn)
        uri = "viking://resources/owner/policy.md"
        result = store.approved("owner", uri)
        self.assertEqual(result.version, "v3")
        self.assertEqual(cursor.execute.call_args.args[1], (uri,))
        conn.set_session.assert_called_once_with(readonly=True)
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()

    def test_revoked_latest_version_blocks_stale_document(self):
        row = ("docs:policy", "v4", "a" * 64, "2026-01-01T00:00:00Z",
               "2026-01-02T00:00:00Z", None, "REVOKED", "b" * 64)
        conn, _ = self.connection(row)
        self.assertIsNone(PostgresManifestStore("synthetic", connect=lambda: conn).approved(
            "owner", "viking://resources/owner/policy.md"))

    def test_company_scope_and_wrong_role_fail_closed(self):
        store = PostgresManifestStore("synthetic", connect=lambda: self.fail("should not connect"))
        self.assertIsNone(store.approved("company:alpha", "viking://resources/alpha/doc.md"))
        conn, _ = self.connection(None, role="database_owner")
        with self.assertRaises(ContextSourceError):
            PostgresManifestStore("synthetic", connect=lambda: conn).approved(
                "owner", "viking://resources/owner/doc.md")


if __name__ == "__main__":
    unittest.main()
