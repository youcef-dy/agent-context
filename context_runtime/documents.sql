-- Proposed additive v2 migration. Do not apply before an approved restore test.
-- Document ingestion and revisions are administrator-only; Hermes has no write grant.
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '15s';
CREATE TABLE adam_info.context_documents (
  id text PRIMARY KEY CHECK (id ~ '^[a-f0-9]{32}$'),
  access_scope text NOT NULL CHECK (access_scope = 'owner'),
  viking_uri text NOT NULL CHECK (viking_uri LIKE 'viking://resources/%'),
  revision integer NOT NULL CHECK (revision BETWEEN 1 AND 1000000),
  source_uri text NOT NULL CHECK (length(source_uri) BETWEEN 1 AND 2048),
  source_version text NOT NULL CHECK (length(source_version) BETWEEN 1 AND 200),
  content_hash text NOT NULL CHECK (content_hash ~ '^[a-f0-9]{64}$'),
  indexed_text_hash text NOT NULL CHECK (indexed_text_hash ~ '^[a-f0-9]{64}$'),
  observed_at timestamptz NOT NULL,
  approved_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at timestamptz,
  state text NOT NULL CHECK (state IN ('APPROVED','REVOKED')),
  approval_reference text NOT NULL CHECK (length(approval_reference) BETWEEN 1 AND 200),
  UNIQUE (access_scope,viking_uri,revision)
);
CREATE INDEX context_documents_current_idx
  ON adam_info.context_documents(access_scope,viking_uri,revision DESC);
REVOKE ALL ON adam_info.context_documents FROM PUBLIC,adam_reader,adam_writer;
GRANT SELECT ON adam_info.context_documents TO adam_reader;
ALTER TABLE adam_info.context_documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY owner_document_read ON adam_info.context_documents FOR SELECT TO adam_reader
  USING (access_scope = 'owner');
