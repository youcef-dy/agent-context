# Data and integration contracts

## Trusted request context

The service host authenticates a profile credential and obtains a `Principal`
containing actor ID, permitted scopes, and issuer. `IdentityDirectory` provides
the credential lookup. Gateway user routing must be independently validated;
this library alone cannot prove which Telegram sender used a shared profile.

The reference scope grammar is `owner` or `company:<id>`. `owner` is valid only
for the one verified owner profile. It is not a generic personal scope shared
by multiple users. Future personal accounts need unique subject scopes and
corresponding storage policies before access is enabled.

`ContextRequest` contains query, scope, purpose (`business`, `memory`,
`document`, or `mixed`), limit, and maximum excerpt characters. Trusted code
constructs the principal; a requested scope must already be granted.

## Evidence packet

Each item supplies:

| Field | Meaning |
| --- | --- |
| `canonical_id` | Stable identity used for deduplication and conflict grouping |
| `source_uri`, `version` | Traceable source location and version/snapshot |
| `content_hash` | Source-version hash; Hindsight uses the recalled-memory text snapshot |
| `excerpt_hash` | Hash of exactly the text returned after truncation |
| `observed_at` | Source event/update time, when known |
| `recorded_at` | Capture or retention time; never fabricated from current time |
| `expires_at` | Optional freshness boundary |
| `scope`, `kind` | Access partition and source category |
| `excerpt_truncated` | Whether the supplied text is incomplete |
| `untrusted_source_text` | Always true; evidence cannot issue agent instructions |

The packet also returns query hash, query time, conflicts, warnings, source
policy and answerability. An empty result is not proof that the underlying
fact does not exist. The library bounds excerpt characters; a host may add
model-specific token accounting. Large metadata fields must also be bounded
when exposing the packet over a network.

## Provider adapters

### PostgreSQL

`PostgresLedger` reads the existing owner-only `adam_info.context_sources` and
`context_versions` through `adam_reader`, TLS verification, read-only
transactions, parameterized queries, and a statement timeout. `LedgerSource`
converts that response into evidence. History includes the recorded approval
reference and its actual assurance level. No write or migration API is exposed.

The existing core tables stay unchanged. The proposed `documents.sql` adds an
owner-only manifest with raw source hash and separate indexed-text hash. It
has not been applied. Its table definition has changed from the earlier draft;
review migration history rather than blindly applying it to an existing table.

### Hindsight

`HindsightSource` calls the documented bank recall endpoint with a bank chosen
by trusted host configuration. It requests bounded `world` and `experience`
results, preserving retention and event timestamps. It currently serves owner
scope only. The REST client permits the recall route, not arbitrary provider
mutations. Provider contract tests use synthetic responses, not a live bank.

The architecture can also use the maintained Hermes provider plugin. Choose
one recall injection path per profile to prevent duplicate context. For this
service implementation, use the explicit adapter path; a native plugin pilot
must not simultaneously auto-inject the same memories. Reflection and retain
are later integration work. Provider credentials must be scoped to the
configured bank wherever supported; a bank name alone is not access control.

### OpenViking

`OpenVikingSource` performs bounded resource searches and explicit content
reads. Every accepted URI needs a current approved manifest in the same scope.
Full reads compare the extracted-text hash before returning an excerpt.
Abstracts are derived search hints, not cryptographic proof of document text;
fetch verified detail before relying on an exact quotation or disputed fact.
Ingestion must publish immutable version URIs and verify L0/L1/L2 readiness.
The current adapter uses L0 abstracts and L2 reads; L1 escalation is planned.

### Live systems / ERP

`ErpSource` describes a proposed `POST /adam/context/search` contract. It is
not an endpoint known to exist in any current Render service. The application
must authorize the user and company itself, bound results, and return
`company_id`, `record_id`, `source_uri`, `content_hash`, `summary`, `updated_at`
and `revision`. A user-bound token comes from trusted host code. Other live
systems need equivalent adapters that preserve their own authorization.

## Target PostgreSQL logical records

The following are logical contracts, not migrations applied by this release:

- `entities` and `aliases`: scoped people, organizations, projects, services;
  canonical IDs, label, evidence, confirmation actor/time and status.
- `relationships`: scoped typed edges, endpoint IDs, source evidence and validity.
- `operating_rules`: scope, trigger, instruction, exceptions, precedence,
  source-message reference, approval reference and superseding revision.
- `source_registry`: connector, external ID, URI, version, source hash,
  event/capture timestamps, ACL reference, sync cursor and tombstone state.
- `artifact_versions` and `artifact_dependencies`: original locations, hashes,
  versions and affected cell/slide/section selectors.
- `provider_projections`: source-version-to-bank/item/URI mapping, indexing
  status, retry identity, last verified time and revocation status.

Use composite scope/ID references, append-only revisions for durable facts,
and an idempotency identity bound to the submitted payload. All persistent
writes need the established approval path. A transaction/outbox can eventually
coordinate approved ledger writes and provider projection jobs, but no automatic
outbox writer is enabled by this repository.

## Agent-facing tools and remaining work

The optional, not-yet-deployed MCP host exposes read-only
`context_provider_status`, `context_bundle`, `context_history`,
`context_document_read`, and `context_project_resolve`. It fixes the principal
to `owner`; the model cannot supply an actor credential, SQL, URL, provider
bank, or company scope. The service token authenticates the host, not an
individual Telegram sender, so the gateway allowlist is a separate gate.
Artifact impact, persistent projects, and any writes remain future work.
Writes retain the same-conversation approval rule and need a separately
reviewed contract.
