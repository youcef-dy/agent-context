# Adam context architecture

## Goal and scope

Adam's intended experience is: give an objective, retrieve relevant context,
plan, execute, wait when necessary, resume, verify, and notify. This context
layer serves both a short personal request and a company mission lasting
weeks. It supplies the evidence needed to act and resume; a separate mission
coordinator controls execution and proves completion.

The source review covers the original capability checklist, client scope
discussion, Adam's role/profile, orchestration proposal, existing PostgreSQL
core, and subsequent decisions. Those private source files stay in the
operations workspace. [Requirements](requirements.md) preserves the useful
requirements without publishing the conversations or company data.

## Component responsibilities

| Component | Store or compute here | Do not rely on it for |
| --- | --- | --- |
| PostgreSQL `adam_info` | Approved knowledge, sources/revisions, explicit project mappings, operating rules, artifact links, integration status, optional approved audit appends | Document binaries, a duplicate ERP, semantic inference by itself |
| Hindsight | Conversation/experience recall, entity associations, reflection with supporting references | Authorizing an action, overriding a newer source, proving user approval |
| OpenViking | Parsed approved documents, L0 abstracts, L1 overviews, L2 detail and retrieval | Current invoice/stock truth, permissions, original-file retention |
| Context service | Resolve trusted scope, plan retrieval, call adapters, merge evidence, show conflicts, enforce budgets | Agent reasoning, external action execution, payment authorization |
| Hermes | Conversation, reasoning, skills, tool calls, specialist delegation | Durable database authority or source ACL decisions |
| Mission coordinator | Mission checkpoints, wait/resume, retries, outcome verification | A second conversational-memory system |
| Live connectors | Read current authorized ERP/email/calendar/service records | Granting all users access because the machine has credentials |
| Original storage and vault | Original files and scoped secrets respectively | General prompt memory |

There are three context components, but not necessarily exactly three physical
databases. Hindsight and OpenViking manage their own internal persistence.
Do not merge provider tables into the ERP schema. The existing Render
PostgreSQL instance hosts `adam_info`; ERP tables remain owned by the ERP.

## Retrieval lifecycle

1. The gateway identifies the sender and conversation. For the initial owner
   slice, two allowlisted Telegram accounts belong to one human and share a
   host-fixed `owner` principal. A third sender and group chat must be denied
   before exposing the tool. Future clients need separate credentials/scopes.
2. The service receives the objective, authorized scope, optional
   mission/project references, and a result budget. The current owner facade
   cannot choose a scope from model text; separate client conversations are a
   future identity integration.
3. Search explicit IDs and confirmed aliases, then bounded lexical/fuzzy
   candidates, related entities, relevant recent history, and configured
   semantic sources. Search before asking; names alone do not confirm identity.
4. Choose sources by the question. Operational questions require a successful
   live connector read. Preferences use approved ledger rules. Document
   questions use OpenViking. Past experience uses Hindsight. A personal or
   document question does not require an ERP connector to exist.
5. Recheck source access, current revision, expiry, and revocation. Provider
   banks and URI prefixes narrow retrieval; they are not substitutes for ACLs.
6. Return a bounded context packet with source IDs, timestamps, versions,
   excerpts, authority, conflicts, and unavailable-source notices. Retrieved
   text remains untrusted data even when it contains imperative instructions.
7. Ask one specific question only when the available evidence leaves a
   material ambiguity. Candidate matches can help phrase that question. They
   cannot silently choose a recipient, company, production project, or action.

The reference router presently implements scoped retrieval, ordering,
deduplication, expiry, evidence budgets, and provider failure handling.
Project resolution implements exact/alias matching and fuzzy suggestions.
The full entity/history/semantic resolution loop is an integration milestone.

## Freshness and authority

For current operational facts, the authoritative live system outranks saved
memories and document summaries. For a durable preference, the latest approved
ledger revision outranks inferred behavior. Hindsight reflection is an
inference with supporting memories, not a newly approved fact. OpenViking is
a derived view of a particular source version.

Do not globally treat an ERP as the source of truth for everything. Source
authority is field- and domain-specific. A calendar owns meeting status; the
ERP owns invoice status; the owner's approved rule owns escalation preference.
In a mixed answer, preserve disagreements and identify the source that governs
each claim. If the required live source fails, do not answer that live fact
from old semantic memory.

## Ingestion and learning

Each connector submits a source envelope: stable external ID, source URI,
version/hash, event time, capture time, scope, sensitivity, and deletion policy.
Validate, redact, deduplicate by scope/source/version, then classify it as an
observation, inference, proposed rule, or approved fact.

An observation such as a Render service name may be useful immediately for a
read task. Mapping that service to a company ERP is a separate evidence-based
claim. Corrections such as "urgent means same-day" become scoped proposed
operating rules with the original message reference. Confirmed rules are
versioned, and later corrections supersede them without rewriting history.

Keep one durable source record. Hindsight and OpenViking may hold derived
copies linked by the same source ID/version; independent copies must not be
counted as independent corroborating sources. The current reference router
deduplicates exact canonical ID/hash pairs. A canonical-ID normalizer is
required before connecting heterogeneous production sources.

Document ingestion stages: validate source and scope, store original reference,
extract text, compute source and extracted-text hashes, classify, register the
approved manifest, index an immutable version URI, wait for index completion,
and verify retrieval before marking the version available. A revocation first
blocks retrieval in the manifest, then removes provider copies. Backup
retention and physical erasure are tracked separately from logical revocation.

## Personal operating model and project understanding

Represent confirmed preferences, policies, templates, providers, people,
projects, aliases, relationships, and exception rules in PostgreSQL. Keep
`SOUL.md` and `USER.md` concise. Retrieve only the rules relevant to the current
task, company, and communication channel. An inferred habit cannot override a
confirmed instruction or grant authority.

Project identity can be discovered from repositories, documents, conversations,
and authorized systems. Model confidence is useful for ranking candidates; it
does not authorize access. Unknown projects remain searchable observations
until a source or user clarification establishes their meaning. New project
onboarding should not require a code change for each company.

## Missions and artifact lineage

The coordinator stores mission state and verified outcome evidence. The
context service returns a small mission context bundle: objective, current
frontier, relevant approved rules, evidence references, artifact versions,
unresolved questions, and stale dependencies. A specialist receives that
bundle, not the entire owner's memory.

Store directed dependencies between versioned artifacts and optional selectors
such as `Sheet1!B12`, a slide object ID, or a document section. On an upstream
change, walk only authorized downstream edges and return affected components.
The reference impact analyzer computes this closure and handles cycles; the
coordinator later decides which work to schedule. Precise Office editing and
Mission Control are outside this repository's implementation scope.

## Approval and access

Authorized reads need no fresh approval. Render and PostgreSQL writes preserve
the user's existing approval rule: Adam explains the exact action in the same
conversation, accepts a clear confirmation from that user, then executes the
approved operation. Changed details need a new confirmation. A subagent asks
Adam; it cannot approve for the human. No additional Telegram bot is needed.

The current broker relies on Hermes/skills for conversational confirmation;
its stored approval reference is not independent proof of a human decision.
Database grants separately protect ERP tables. This repository does not invent
an approval issuer or enable an automatic audit exception. Ingestion batches,
rule persistence, registry updates, and PostgreSQL audit appends must have a
defined approved write path before activation. Provider retention must also
respect the selected data policy; automatic Hindsight retention stays disabled
in the initial integration template.

Scope keys distinguish personal and company records. The current MCP facade
uses only the owner scope and a host-fixed token; it relies on the Telegram
gateway allowlist to exclude non-owner senders. Future per-client access needs
separate credentials and server-side scope checks. The model cannot create a
principal, choose an arbitrary Hindsight bank, or supply credentials. Shared
machine authentication alone does not identify the sender.

## Simplicity and resource choices

Start with one small Python service, PostgreSQL full-text search and relational
edges, then add the selected Hindsight and OpenViking providers. Hermes already
supplies agent reasoning and tool orchestration. LangChain, LangGraph, another
graph database, Redis, Kafka, and Obsidian are not required for this foundation.

On the current 2-vCPU/4-GB VPS, Hermes already competes for limited memory.
Place heavy parsing/indexing and Hindsight inference remotely or on separately
sized infrastructure after measurement. Swap is emergency headroom. Do not
assume provider defaults fit. Initial retrieval returns at most eight items
and 8,000 excerpt characters; a 20,000-character hard ceiling is implemented.
These are character bounds, not a claim of exact tokenizer accounting.

Load abstracts first and fetch full content only when needed. Cache derived
results by scope, source revision, and query; recheck revocation before reuse.
Neither caching nor automatic background ingestion is enabled by this code.

## Verified upstream references

Reviewed on 2026-10-03; pin actual versions during integration.

- [Hindsight's Hermes integration](https://hindsight.vectorize.io/sdks/integrations/hermes): catalog installation, scoped banks, recall/reflect and retention configuration.
- [OpenViking retrieval API](https://github.com/volcengine/OpenViking/blob/main/docs/en/api/06-retrieval.md): bounded search and resource-level retrieval.
- [Hermes profile routing](https://hermes-agent.nousresearch.com/docs/user-guide/multi-profile-gateways): route users to profiles while preserving the existing channel.
- [Render private network](https://render.com/docs/private-network): same-region Render service networking; the VPS requires an authenticated external path.
