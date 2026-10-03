# Agent Context for Adam

Context architecture and executable retrieval foundation for Adam, a universal
personal AI Chief of Staff built on Hermes. The scope spans authorized personal
and company work: people, projects, preferences, conversations, documents,
current business records, and mission evidence.

## The three components

| Component | Responsibility | Authority |
| --- | --- | --- |
| PostgreSQL / `adam_info` | Approved facts, identity mappings, source versions, provenance, relationships and artifact references | Durable record of what was approved and when |
| Hindsight | Recall of experience and conversations; on-demand reflection | Supporting memory; synthesized beliefs remain attributable and revisable |
| OpenViking | Large-document organization and progressive retrieval | Derived index of approved, versioned originals |

The context service binds identity, searches permitted sources, resolves
references, applies budgets, and returns evidence. Live ERP, email, calendar,
and other APIs remain authoritative for changing facts. Hermes owns reasoning
and the conversation; the mission coordinator owns execution, waits, and
completion checks. Secrets stay in the configured vault.

## Start here

- [Architecture and decisions](docs/architecture.md)
- [Interactive architecture](docs/context-architecture.html) — download and open locally
- [Requirements and acceptance criteria](docs/requirements.md)
- [Data and integration contracts](docs/contracts.md)
- [Implementation phases and current status](docs/roadmap.md)
- [Deployment and recovery](docs/operations.md)
- [Observed production status](docs/production-status.md)

## Run the reference code

Python 3.11 or newer; the default tests and demo need no third-party packages.
From this repository root:

```console
python -m unittest discover -s context_runtime -p "test_*.py" -v
python -m context_runtime.demo
```

`context_runtime/` contains a bounded router, a legacy ledger adapter, proposed
ERP contract adapter, OpenViking reads, scoped project resolution, artifact
impact analysis, and synthetic tests. These are reusable library components.
No network connection or database migration is made by the demo or tests.

## Delivery status

This repository is a **design plus tested reference implementation**. It is
not a deployed three-provider context service. The earlier owner-only PostgreSQL core remains
in the Adam operations repository; it is integrated here through a port rather
than copied with deployment credentials or infrastructure administration code.
Hindsight runtime integration, authorized ingestion, persistent project and
lineage repositories, the MCP host, and live acceptance tests are rollout work.
See the [status matrix](docs/roadmap.md) before enabling a capability.

Publication of this repository does not deploy or modify Render, Hermes,
PostgreSQL, or the Telegram bot.
