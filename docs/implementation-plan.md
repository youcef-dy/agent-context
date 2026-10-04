# Final context-layer implementation plan

Status baseline: 2026-10-05. Adam has one human owner using two allowlisted
Telegram accounts on the same bot. The gateway's `profile_routes` map is empty;
both accounts currently use the default profile. Before any new owner-context
tool is exposed, prove that both IDs belong to the owner, a third ID and group
chat are denied, and no client can use the shared profile. Separate client
access is a future identity project, not a reason to duplicate owner memory.

## Selected architecture

Keep three distinct responsibilities, not three competing authorities:
PostgreSQL `adam_info` records approved facts and provenance; Hindsight recalls
personal experience; OpenViking indexes approved, versioned documents. A small
read-only context facade combines permitted evidence and marks gaps. Live ERP
records remain authoritative for current business facts. Hermes reasons over
the packet; the mission coordinator owns execution and checkpoints.

Use explicit Hindsight recall through the facade for the first production
slice. Do **not** also enable the native Hermes Hindsight provider: two recall
paths would duplicate context, and its current defaults automatically retain
and recall turns. Reconsider the maintained native provider only after the
retention and provenance policy is tested. The deprecated standalone
`hindsight-hermes` pip plugin must not be installed.

## Delivery sequence and exit gates

1. **Read-only owner slice.** Package the router behind a bearer-authenticated
   MCP facade with a host-fixed owner principal, bounded results, and no write
   tools. Connect the existing restricted PostgreSQL reader and private
   Hindsight recall endpoint. Keep OpenViking and company/ERP scopes disabled.
   Exit: synthetic contract tests, wrong-token HTTP test, no audit writes, and
   a live Telegram query that reports its sources and missing providers.
2. **Hindsight retention and recovery.** Restore an encrypted GitHub-exported
   Hindsight snapshot into a fresh isolated instance. Automatic retention is
   **off by owner decision**. Use only a dedicated synthetic bank for retain,
   recall, provenance, deletion, restart, and inference-cost tests. Real
   conversation retention needs a later explicit change. Exit: a synthetic
   fact is recalled in a new test session and traced to its source/time.
3. **Versioned documents.** Use only synthetic documents for the first pilot,
   by owner decision, and choose an
   OpenViking placement with measured RAM, disk, and persistent storage. The
   4 GiB VPS currently has little free memory and uses swap; do not add the
   default indexing stack there without a peak-load test. Apply the owner-only
   manifest migration only after an exact approved write and restore test.
   Ingest immutable source versions, verify summary search and L2 text hashes, and
   block revoked versions before provider deletion. Exit: cited retrieval of
   the synthetic approved version with measured context savings. A real corpus
   requires a later explicit scope decision.
4. **Projects and live business facts.** Persist reviewed project aliases and
   source mappings; keep Render service names as observations. Identify the
   actual ERP and implement its user/company-authorized read endpoint before
   answering company operational questions. Exit: an unknown project prompts
   for clarification and ERP outage never turns old memory into current truth.
5. **Production acceptance.** Test the two-ID Telegram allowlist, denied third
   ID/group, prompt injection in a document, duplicate source across providers,
   provider outage, restart, and an isolated restore. Record latency, result
   quality, token volume, memory peak, and cost. Only then mark the
   three-provider layer production-ready.

## Current evidence and constraints

- Live: `adam_info` lexical search/history through the existing PostgreSQL
  broker; Hermes MCP read checks pass. Render MCP reads pass. No silent audit
  write is enabled.
- Pilot: Hindsight runs privately with authenticated API and synthetic bank;
  Hermes has no active Hindsight memory provider. The essential GitHub backup
  contains a consistent Hindsight export, but a fresh-instance restore has not
  been proven.
- Code-only: OpenViking adapter, manifest contract, project catalog, and
  router pass synthetic tests. No OpenViking service, approved corpus, applied
  manifest migration, ERP business adapter, or deployed facade exists yet.
- Governance: authorized reads need no confirmation; every Render or
  PostgreSQL write still needs the established same-conversation approval.
  This plan authorizes no migration, automatic retention, or real-data ingest.

This sequence intentionally postpones LangGraph, a second memory framework,
and a separate graph database. They do not close the current missing path from
Telegram to permitted, cited context.
