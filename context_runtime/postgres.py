"""Read the existing adam_info core through its restricted PostgreSQL role."""

from contextlib import contextmanager
import re

from .core import ContextSourceError


class PostgresLedger:
    def __init__(self, reader_dsn: str, *, connect=None):
        self.reader_dsn, self.connect = reader_dsn, connect

    @contextmanager
    def cursor(self):
        conn = None
        try:
            if self.connect:
                conn = self.connect()
            else:
                import psycopg2
                import certifi
                conn = psycopg2.connect(
                    self.reader_dsn, connect_timeout=10, sslmode="verify-full",
                    sslrootcert=certifi.where(),
                    options="-c default_transaction_read_only=on -c statement_timeout=10000 -c search_path=pg_catalog")
            conn.set_session(readonly=True)
            with conn.cursor() as cur:
                cur.execute("SELECT current_user")
                if cur.fetchone() != ("adam_reader",):
                    raise ContextSourceError("ledger requires the restricted reader role")
                yield cur
        except ContextSourceError:
            raise
        except Exception:
            raise ContextSourceError("PostgreSQL ledger is unavailable") from None
        finally:
            if conn is not None:
                try:
                    conn.rollback()
                finally:
                    conn.close()

    @staticmethod
    def rows(cur):
        names = [column[0] for column in cur.description]
        return [dict(zip(names, row)) for row in cur.fetchall()]

    def search(self, query: str, limit: int = 8) -> dict:
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 300:
            raise ValueError("invalid ledger query")
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("invalid ledger limit")
        with self.cursor() as cur:
            cur.execute("""WITH latest AS (
                SELECT DISTINCT ON (memory_id) * FROM adam_info.context_versions
                WHERE access_scope='owner' ORDER BY memory_id,revision DESC)
                SELECT v.memory_id,v.revision,v.title,v.body,v.observed_at::text,
                  v.recorded_at::text,v.expires_at::text,s.source_uri,s.content_hash
                FROM latest v JOIN adam_info.context_sources s
                  ON s.id=v.source_id AND s.access_scope=v.access_scope
                WHERE v.state='ACTIVE'
                  AND (v.expires_at IS NULL OR v.expires_at>CURRENT_TIMESTAMP)
                  AND to_tsvector('simple',v.title || ' ' || v.body)
                    @@ plainto_tsquery('simple',%s)
                ORDER BY v.recorded_at DESC,v.id LIMIT %s""", (query, limit))
            items = self.rows(cur)
        return {"items": items, "scope": "owner", "audit_written": False}

    def history(self, memory_id: str, limit: int = 10) -> dict:
        if not isinstance(memory_id, str) or not re.fullmatch(r"[a-f0-9]{32}", memory_id):
            raise ValueError("invalid memory identifier")
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("invalid history limit")
        with self.cursor() as cur:
            cur.execute("""SELECT v.memory_id,v.revision,v.state,v.title,v.body,
                v.observed_at::text,v.recorded_at::text,v.approval_reference,
                v.approval_basis,s.source_uri,s.content_hash
                FROM adam_info.context_versions v JOIN adam_info.context_sources s
                  ON s.id=v.source_id AND s.access_scope=v.access_scope
                WHERE v.access_scope='owner' AND v.memory_id=%s
                ORDER BY v.revision DESC LIMIT %s""", (memory_id, limit))
            items = self.rows(cur)
        return {"items": items, "scope": "owner", "audit_written": False}
