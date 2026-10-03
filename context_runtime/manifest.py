"""PostgreSQL-approved document manifest; the vector index is never authority."""

from __future__ import annotations

from .adapters import DocumentManifest
from .core import ContextSourceError


class PostgresManifestStore:
    def __init__(self, reader_dsn: str, connect=None):
        self.reader_dsn, self.connect = reader_dsn, connect

    def approved(self, scope: str, uri: str) -> DocumentManifest | None:
        if scope != "owner" or not uri.startswith("viking://resources/"):
            return None  # No company manifest grants in the first migration.
        if self.connect:
            conn = self.connect()
        else:
            import psycopg2
            import certifi
            conn = psycopg2.connect(
                self.reader_dsn, connect_timeout=10, sslmode="verify-full",
                sslrootcert=certifi.where(),
                options="-c default_transaction_read_only=on -c statement_timeout=10000 -c search_path=pg_catalog")
        try:
            conn.set_session(readonly=True)
            with conn.cursor() as cur:
                cur.execute("SELECT current_user")
                if cur.fetchone()[0] != "adam_reader":
                    raise ContextSourceError("document manifest needs the restricted reader")
                cur.execute("""SELECT source_uri,source_version,content_hash,observed_at::text,
                    approved_at::text,expires_at::text,state,indexed_text_hash FROM adam_info.context_documents
                    WHERE access_scope='owner' AND viking_uri=%s
                    ORDER BY revision DESC LIMIT 1""", (uri,))
                row = cur.fetchone()
            if not row or row[6] != "APPROVED":
                return None
            return DocumentManifest(uri, "owner", row[0], row[2], row[1], row[3], row[4], row[5], row[7])
        except ContextSourceError:
            raise
        except Exception:
            raise ContextSourceError("document manifest unavailable") from None
        finally:
            conn.rollback()
            conn.close()
