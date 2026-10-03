# Requirements and acceptance criteria

This is a sanitized interpretation of Adam's product specification and the
owner's subsequent context-layer decisions. Source review: 2026-10-03.
Private discussions and production information are deliberately not copied.

| Requirement | Architecture response | Acceptance evidence | Status in this repository |
| --- | --- | --- | --- |
| Universal personal Chief of Staff | Personal and company scopes; configurable connectors, no hard-coded ERP project | A personal request works without ERP; unauthorized company scope is denied | Router tests |
| Search before asking | Exact IDs/aliases, fuzzy candidates, history and semantic search before clarification | Misspelling yields suggestions without falsely confirming a project | Catalog implemented; combined search remains |
| Cross-source understanding | Canonical source references and authority-aware evidence packet | Mixed source results cite versions and expose conflicting hashes | Router tests; canonical cross-provider mapping remains |
| Conversational recall | Scoped Hindsight bank, bounded recall; optional reflection | A permitted past fact is recalled after restart with supporting references | Recall adapter contract tests; live test remains |
| Large-document context | OpenViking abstracts first; bounded detail read | Revoked or modified indexed document cannot return approved detail | Manifest and integrity tests; ingestion remains |
| Durable corrections | Proposed preference/policy with source and append-only approved revisions | Correction survives a fresh conversation; earlier revision remains inspectable | Existing ledger read/history adapter; learning write workflow remains |
| Traceability | Separate event, capture, approval, retrieval times | Explain when and where a fact entered the system and who confirmed it | Evidence timestamps and history contract |
| New project understanding | Resource observations, aliases, reviewed mappings and provenance | New service stays an observation until meaning is supported | Catalog tests |
| Current business facts | Authoritative live connector, bounded company scope | ERP outage cannot silently turn old recall into invoice truth | ERP contract and failure tests; actual ERP API remains |
| Multiple Telegram users | Trusted profile credentials and isolated scopes | Wrong sender cannot read another user's memory through the same bot | Identity library tests; gateway acceptance remains |
| Long missions | Context bundle references coordinator checkpoint and evidence | Restart resumes from durable mission frontier with applicable rules | Contract only; mission engine is external work |
| Corporate documents | Approved brand/template/identity records scoped by company | Correct organization's versioned template is returned | Data contract; connector corpus remains |
| Artifact dependencies | Versioned edges with cell/slide/section selectors | Dataset change flags only affected model cells and slides | Impact-analysis tests; persistent edges remain |
| Reads without prompts | Read methods never append an implicit PostgreSQL audit row | Read-only role, rollback, no commit | PostgreSQL adapter tests |
| Write confirmation in existing chat | Exact action, same user, approval reference, idempotent execution | Yes/no/details tested in the existing Adam conversation | Documented contract; no new write tools enabled |
| Resilience and honest completion | Provider-specific degradation, bounded results, explicit gaps | Provider failures return partial/unavailable status; no false completion | Router tests; load/restore/provider tests remain |
| Low operations cost | One context service, relational edges, optional providers, staged rollout | Measured RAM, latency, token budget and backup restore | Design; deployment measurements remain |

## Product boundaries

This package supplies evidence and context contracts. It does not replace an
ERP, implement a full CRM, control a computer, send email, authorize payments,
edit Office files, or run the mission coordinator. Those capabilities consume
its scoped context and return outcome evidence through their own integrations.

## Evaluation set

Use synthetic fixtures first, then an owner-approved representative set:

1. A preference corrected twice; ask both current preference and its history.
2. Two people with the same first name in different companies.
3. A misspelled project alias and an entirely new project.
4. An invoice whose cached document disagrees with its live status.
5. A document containing instructions to disclose another user's memory.
6. The same source copied into all three components; count it once as evidence.
7. A revoked document and a changed indexed file at an old URI.
8. A dataset-to-spreadsheet-to-slide chain with one unaffected branch.
9. A recalled fact with no reliable timestamp; do not fabricate a capture date.
10. Provider outage, gateway restart, duplicate ingestion, and restore.

Record evidence precision, missed relevant records, citation validity,
clarification frequency, latency, returned tokens, and resource use. Permission
leaks and incorrect recipient/project selection are zero-tolerance failures.
Do not promise a benchmark score or fixed token saving without measuring Adam's
own documents and workflows.
