# Deployment and recovery

## Placement

Hermes currently runs in Docker on a small VPS. Keep the context service
lightweight and private. Place database-facing code beside Render PostgreSQL
when using its private network; otherwise use verified TLS and the restricted
role through the explicitly authorized external path. Render's private network
does not automatically include the VPS or its WireGuard network.

Hindsight and OpenViking require separate sizing and inference configuration.
Do not bundle their full default stacks into Hermes's constrained container.
Measure steady RAM, peak parsing/indexing RAM, disk growth, latency and provider
cost. Set explicit container limits and retain headroom for Hermes and the OS.

## Configuration and secrets

The reference code does not automatically load `.env`. A service host should
resolve credentials from the existing vault and inject only each adapter's
required value. Suggested host variable names are:

```text
ADAM_CONTEXT_READER_DSN
HINDSIGHT_API_URL
HINDSIGHT_API_KEY
OPENVIKING_API_URL
OPENVIKING_API_KEY
```

Use `Authorization: Bearer` for Hindsight and `X-API-Key` for OpenViking
search/content reads. OpenViking's root key is for administration; provision
an account/user data key for this adapter. The `JsonHttp` constructor defaults
to bearer auth; pass `auth_header="X-API-Key"` for OpenViking. Do not confuse
an API key for the OpenViking service with separate embedding/VLM model keys.

Principal bindings, bank mappings and collection prefixes are trusted
configuration. Use one profile credential per permitted identity/scope. Keep
admin migration credentials outside the running agent/service. Do not log
connection strings, request bodies, source excerpts or authorization headers.

The same Telegram bot remains the user interface. Treat routing profiles as
one isolation layer and service-side scope checks as another. Verify both with
two actual senders and a group chat before granting owner context.

## Database migration

`context_runtime/documents.sql` is a proposed additive table for the existing
`adam_info` schema and `adam_reader`/`adam_writer` roles. It is not a fresh
database bootstrap and is not applied on import or startup. Review the current
schema and migration ledger, obtain the applicable write approval, and apply
only after an isolated restore test. Record the approved SQL checksum.

The table grants only reader access; approved ingestion is administrator-only
until a narrow writer operation is implemented. Never grant Hermes an owner
role or enable general SQL. Do not run a migration from an MCP tool.

## Backup and recovery

Back up the authoritative PostgreSQL records and original documents, including
project mappings and source/projection metadata. Follow Hindsight's supported
backup/export procedure for its service mode and retain required bank policy.
OpenViking indexes should be backed up or reproducibly rebuilt from approved
original versions; measure rebuild time before relying on that strategy.

Encrypt backups, keep an off-platform copy, and test restoration in an isolated
environment. Restore scope policies and revocation records before opening
retrieval. A context rollback disables the new adapter/provider and restores
its previous configuration; it must never overwrite live ERP data.

Logical revocation and physical deletion differ. Track provider deletions,
derived summaries and backup expiry. Do not promise immediate complete erasure
when an approved retention policy preserves encrypted backups.

## Diagnostics

Track request ID, principal/scope identifier, source availability, latency,
returned item/character/token counts and failure class. Hash a query only when
needed for correlation; hashes of short sensitive queries are not anonymization.
Persistent PostgreSQL traces require the established approval policy.

Use a source availability matrix in status responses. An installed package, a
reachable endpoint, successful authentication and a verified retrieval are
different states. Do not report "connected" merely because an HTTP endpoint
responds. Health checks must not retain synthetic facts or mutate production.

## Integration references

- [Hindsight Hermes integration](https://hindsight.vectorize.io/sdks/integrations/hermes)
- [Hindsight recall contract](https://hindsight.vectorize.io/developer/api/recall)
- [OpenViking retrieval API](https://github.com/volcengine/OpenViking/blob/main/docs/en/api/06-retrieval.md)
- [Render private network](https://render.com/docs/private-network)
- [Hermes profile gateways](https://hermes-agent.nousresearch.com/docs/user-guide/multi-profile-gateways)
