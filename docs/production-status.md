# Production status

Checked 2026-10-03 from the running Hermes container on Adam's VPS. This is
an observed status, not a declaration that all context components are live.

| Component | Current state | Acceptance gate |
| --- | --- | --- |
| PostgreSQL `adam_info` | Live through the existing broker. MCP connected; `context_status` and read-only `context_search` succeeded. | Repeat a two-user Telegram scope test before widening access. |
| Hindsight | Adapter and synthetic tests only. No configured Hindsight endpoint, bank, or credential was found in Hermes's environment. | Provision a dedicated bank and credential; prove auth, isolated retain/recall, restart, deletion, and cost controls. |
| OpenViking | Adapter and synthetic tests only. No configured OpenViking endpoint or credential was found in Hermes's environment. | Pin a server image, configure embedding and VLM models, use a non-root data key, approve a versioned document, then prove indexed retrieval and revocation. |
| Render metadata | MCP connects, but the `list_services` read timed out in the latest probe. | Diagnose upstream latency separately; this does not invalidate the PostgreSQL context read. |

The VPS has 2 vCPU, 4 GiB RAM, 80 GiB disk and 2 GiB swap. At the inventory
check, about 2.9 GiB RAM and 52 GiB disk were available. Hermes has a 3 GiB
container memory limit; the broker has 256 MiB. Do not run both additional
providers on this host without measured peak-memory tests and independent
limits. Swap is an emergency buffer, not capacity planning.

The Bitwarden name-only inventory did not finish within its bounded check.
Thus a secret's absence from Hermes's environment does not prove absence from
the vault. Never paste its value in an issue or chat. Once credentials are
ready, inject them through the existing host-side secret process and confirm
only names/health states in logs.

No document migration, Hindsight retain, OpenViking ingest, Hermes restart,
or new provider container was performed by this release. Those operations
need separate live validation, rollback and backup checks. PostgreSQL and
Render writes retain the same-conversation human approval requirement.
