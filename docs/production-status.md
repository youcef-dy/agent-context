# Production status

Checked 2026-10-03 from the running Hermes container on Adam's VPS. This is
an observed status, not a declaration that all context components are live.

| Component | Current state | Acceptance gate |
| --- | --- | --- |
| PostgreSQL `adam_info` | Live through the existing broker. MCP connected; `context_status` and read-only `context_search` succeeded. | Repeat a two-user Telegram scope test before widening access. |
| Hindsight | Self-hosted API-only pilot runs in private Docker networks. A dedicated synthetic bank passed retain, recall, auth and restart-persistence checks; Hermes can reach `/health` but its plugin is **not** connected. No real conversation was retained. | Isolate both Telegram senders at the service boundary, arrange off-host backup/restore, move beyond embedded pg0 for production, then test deletion, cost and real-session behavior. |
| OpenViking | Adapter and synthetic tests only. No configured OpenViking endpoint or credential was found in Hermes's environment. | Pin a server image, configure embedding and VLM models, use a non-root data key, approve a versioned document, then prove indexed retrieval and revocation. |
| Render metadata | MCP connects, but the `list_services` read timed out in the latest probe. | Diagnose upstream latency separately; this does not invalidate the PostgreSQL context read. |

The VPS has 2 vCPU, 4 GiB RAM, 80 GiB disk and 2 GiB swap. Hermes has a 3 GiB
container memory limit, the broker 256 MiB, and Hindsight 2250 MiB (no swap).
After a restart Hindsight used about 743 MiB at idle; this is not a peak-load
measurement. Do not add OpenViking here without peak-memory and disk tests.
Swap is an emergency buffer, not capacity planning.

Hindsight uses local embeddings/reranking but the existing Gemini API for
memory extraction and recall. The API-only image is pinned by digest and has
no published ports. Its pg0 volume is persistent across container restart,
but embedded pg0 is a pilot choice, not the recommended production database.
The Hindsight API key is stored only in a root-owned host env file. It grants
the instance access to all banks, so a bank-name template alone does not
establish a secure cross-user boundary. Hermes's `gateway.profile_routes` is
currently empty; automatic retention/recall remains disabled to avoid mixing
owner and client memory on the shared Telegram bot.

The Bitwarden name-only inventory did not finish within its bounded check.
Thus a secret's absence from Hermes's environment does not prove absence from
the vault. Never paste its value in an issue or chat. Once credentials are
ready, inject them through the existing host-side secret process and confirm
only names/health states in logs.

No real document migration, Hindsight conversation retention, OpenViking
ingest, Hermes restart, or PostgreSQL/Render write was performed. The only
Hindsight write was an explicitly synthetic fact in `adam-hindsight-smoke`.
PostgreSQL and Render writes retain the same-conversation human approval rule.
