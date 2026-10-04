# Implementation phases and delivery status

## Current repository

| Area | Delivered | Still required before live use |
| --- | --- | --- |
| Architecture | Source-reviewed design, component ownership, diagram, requirements | Owner review of rollout decisions |
| Retrieval | Scope validation, priorities, budgets, deduplication, conflicts, timestamps; read-only owner facade | Production source mapping, token metrics, concurrency/deadlines |
| PostgreSQL | Restricted read/history adapter and proposed document manifest | Existing core connection test, manifest migration/restore exercise |
| Hindsight | Owner recall REST adapter; private API-only VPS pilot; synthetic auth, retain/recall and restart checks | Two-ID owner allowlist test, fresh-instance restore, deletion/load/cost tests, real session validation |
| OpenViking | Approved search/detail adapter, text integrity and revocation checks | Parser/ingestion workflow, immutable index, L1 adapter and recovery tests |
| Project understanding | Observations, exact/alias resolution, fuzzy suggestions | Persistent registry, evidence search across history/semantic providers |
| Identity | Per-profile credential-to-principal library; host-fixed owner MCP facade | Verify both owner IDs and reject a third ID/group on the existing bot |
| Artifact context | Scoped dependency impact analysis | Persistent artifact edges and coordinator integration |
| Operations | Packaging, offline demo, CI configuration, rollout/recovery guide | Deploy the tested MCP facade, load testing, real end-to-end acceptance |

## Phase 1: Package and validate the foundation

Publish this standalone repository, run synthetic tests and the offline demo,
and review architecture against the requirements. Keep the prior operations
repository as the deployment history. Do not copy its private transcripts,
environment files, keys, screenshots, or administrative scripts.

## Phase 2: Bind the existing bot to scoped context

Use the existing Telegram bot. The two currently allowed IDs belong to the
same owner and use the default Hermes profile; `profile_routes` is empty.
Before exposing the new owner tool, prove both IDs are authorized and a third
ID/group is denied. Bind the facade to a fixed owner principal and restricted
PostgreSQL reader. Do not infer identity from model-supplied tool arguments.

Exit: an allowed owner account retrieves a known source; an unallowed account
cannot invoke it; reads do not require confirmation or silently persist audit
records. Future client users require distinct credentials and scopes.

## Phase 3: Durable context and learning

Add reviewed entity, rule, registry and artifact records to `adam_info` through
additive migrations. Reuse existing source/version/history records. Connect
confirmation in the existing conversation to the reviewed write operation.
Add payload-bound idempotency, revisions and source evidence to every write.

Exit: a correction survives a new session, history shows original source and
approval reference, and a duplicate confirmed operation does not duplicate data.

## Phase 4: Hindsight experience recall

The self-hosted API-only pilot is pinned and its synthetic bank passed retain,
recall and restart checks. Next, prove fresh-instance restore, two-ID owner
allowlist behavior, provenance, deletion, load and inference cost. Keep
automatic retention off. Use only explicit synthetic retain operations until
the owner approves a real-data policy.

Exit: a permitted past event is recalled across sessions; unrelated user memory
is inaccessible; provider failure leaves other context functions available.

## Phase 5: OpenViking document pipeline

Start with synthetic documents only. Build approved ingestion from an
authorized source directory/storage connector after placement and memory
headroom are measured.
Preserve original references, versions, content hashes and extracted-text
hashes. Track asynchronous indexing to completion. Test categorization,
abstract-to-detail escalation, duplicates, reindex and revocation.

Exit: questions retrieve correct source versions with lower measured context
volume than loading full documents; modified or revoked versions are blocked.

## Phase 6: Live sources and cross-source understanding

Connect the actual ERP only after its identity and API authorization are known.
Add other connectors as relevant workflows need them. Wire history, aliases,
relationships and semantic candidates into the clarification loop. Connect
artifact impact results and mission context bundles to the coordinator.

Exit: Adam can resolve an implicit reference from permitted evidence, ask when
ambiguity remains, and cite live facts alongside document and memory evidence.

## Phase 7: Production acceptance and recovery

Run representative adversarial, outage, duplicate-delivery, resource and
restore tests. Test the actual Telegram experience and same-conversation
confirmation. Keep measurements and pinned configuration with each rollout.
Declare each provider live only after its complete path has been exercised.

Publishing the design and passing mocked adapter tests complete Phase 1, not
all seven phases. Runtime deployment follows a separately reviewed rollout.
