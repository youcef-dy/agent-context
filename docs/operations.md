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

## Hindsight pilot on the VPS

The Hindsight API-only image is pinned by digest in `ops/deploy_hindsight_vps.py`.
It runs as `adam-hindsight` with no published ports, connected to
`adam-hermes-broker` for private access and `adam-render-egress` for the Gemini
API. Local models handle embeddings and reranking; Gemini handles LLM tasks.
The 2250 MiB memory limit has no additional container swap. A root-only
`/etc/adam-hindsight.env` holds the instance API token and Gemini key, and
`adam-hindsight-pg0` persists the pilot database. Do not commit either secret
or dump the env file into logs.

Run the value-silent checks from an authorized VPS shell as root:

```console
python3 ops/verify_hindsight_vps.py
python3 ops/recall_hindsight_smoke.py
```

The second check reads only the dedicated synthetic bank. `ops/smoke_hindsight_vps.py`
creates a synthetic fact and is not a routine health check. The service's
restart policy is `unless-stopped`; after any restart wait for `/health` before
testing recall. `ops/check_hermes_hindsight_reachability.py` is a credential-free
health request to run inside Hermes; it returned HTTP 200 in the pilot. A green
container state alone is insufficient.

This is not yet an Adam-facing memory service. The essential encrypted GitHub
backup now includes a verified Hindsight export, but a fresh-instance restore
has not been tested and Render PostgreSQL is not covered. Embedded pg0 remains
a pilot choice; Hindsight recommends external PostgreSQL with pgvector for
production. The two Telegram IDs belong to one owner, but the current shared
API token can access every bank. Test the two-ID allowlist, denial of a third
sender/group, deletion and resource peaks. Automatic retention is explicitly
off by owner decision; do not turn on a native plugin with default retention.
The older full Hindsight image and two stopped start attempts remain on the
VPS; they are not part of the running path.

## Configuration and secrets

The reference code does not automatically load `.env`. The optional
`context_runtime.serve` process reads only the restricted PostgreSQL DSN from
its environment and tokens from private files owned by the service user.
It is not deployed. Its currently supported variables are:

```text
ADAM_CONTEXT_READER_DSN
ADAM_CONTEXT_MCP_TOKEN_FILE
ADAM_CONTEXT_ALLOWED_HOSTS
ADAM_CONTEXT_BIND
ADAM_CONTEXT_HINDSIGHT_URL
ADAM_CONTEXT_HINDSIGHT_KEY_FILE
ADAM_CONTEXT_HINDSIGHT_BANK
```

The Hindsight variables are optional and must refer to a fixed synthetic bank
until retention and restore gates pass. OpenViking is not wired into this host
yet. Keep the MCP endpoint private and require the host-fixed owner token; the
two Telegram accounts must pass gateway allowlist tests before attachment.

Use `Authorization: Bearer` for Hindsight and `X-API-Key` for OpenViking
search/content reads. OpenViking's root key is for administration; provision
an account/user data key for this adapter. The `JsonHttp` constructor defaults
to bearer auth; pass `auth_header="X-API-Key"` for OpenViking. Do not confuse
an API key for the OpenViking service with separate embedding/VLM model keys.

Principal bindings, bank mappings and collection prefixes are trusted
configuration. Both current Telegram accounts map to one owner; future clients
need separate credentials and scopes. Keep admin migration credentials outside
the running agent/service. Do not log
connection strings, request bodies, source excerpts or authorization headers.

The same Telegram bot remains the user interface. Its `profile_routes` map is
empty, so sender isolation currently relies on the allowlist, not separate
profiles. Verify both owner IDs and rejection of a third ID/group before
granting the shared profile access to the owner facade.

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
