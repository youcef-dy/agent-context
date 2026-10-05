# Production status

Checked 2026-10-05 from the running Hermes container on Adam's VPS. This is
an observed status, not a declaration that all context components are live.

| Component | Current state | Acceptance gate |
| --- | --- | --- |
| PostgreSQL `adam_info` | Live through the existing broker. MCP connected; `context_status` and read-only `context_search` succeeded. | Verify the two allowlisted owner IDs and deny a third ID/group before widening access. |
| Hindsight | Self-hosted API-only pilot runs in private Docker networks. A dedicated synthetic bank passed retain, recall, auth and restart-persistence checks; no Hermes memory provider is active. No real conversation was retained. | Complete fresh-instance restore from the encrypted off-host export, then test deletion, cost, provenance and real-session behavior before retention. |
| OpenViking | Adapter and synthetic tests only. No configured OpenViking endpoint or credential was found in Hermes's environment. The owner approved no real documents yet. | Pin a server image, configure embedding and VLM models, use a non-root data key, ingest synthetic documents only, then prove indexed retrieval and revocation. |
| Render metadata | MCP connects and the current `list_services` read succeeded. | Do not infer which service is the ERP from its name. |

The VPS has 2 vCPU, 4 GiB RAM, 80 GiB disk and 2 GiB swap. Hermes has a 3 GiB
container memory limit, the broker 256 MiB, and Hindsight 2250 MiB (no swap).
In the latest read-only snapshot, Hermes used about 2.19 GiB, Hindsight
220 MiB, and the broker 33 MiB; host memory available was about 1.0 GiB and
654 MiB of swap was in use. These are point-in-time values, not a peak-load
measurement. Do not build or add OpenViking or a second Hindsight instance on
this 4 GiB host. The possible 8 GiB resize awaits a credit and cost check.
Swap is an emergency buffer, not capacity planning.

Hindsight uses local embeddings/reranking but the existing Gemini API for
memory extraction and recall. The API-only image is pinned by digest and has
no published ports. Its pg0 volume is persistent across container restart,
but embedded pg0 is a pilot choice, not the recommended production database.
The Hindsight API key is stored only in a root-owned host env file. It grants
the instance access to all banks, so a bank-name template alone does not
establish a secure cross-user boundary. Hermes's `gateway.profile_routes` map
is empty. The Telegram allowlist has two IDs that the owner says are both
theirs. Automatic retention/recall remains disabled until the allowlist and
source policy pass live acceptance tests.

The Bitwarden name-only inventory did not finish within its bounded check.
Thus a secret's absence from Hermes's environment does not prove absence from
the vault. Never paste its value in an issue or chat. Once credentials are
ready, inject them through the existing host-side secret process and confirm
only names/health states in logs.

The active essential GitHub backup includes a consistent Hindsight export,
download/hash verification, and ZIP integrity check. It does not prove a
fresh-instance Hindsight restore or cover Render PostgreSQL. No real document
migration, Hindsight conversation retention, OpenViking
ingest, Hermes restart, or PostgreSQL/Render write was performed. The only
Hindsight write was an explicitly synthetic fact in `adam-hindsight-smoke`.
PostgreSQL and Render writes retain the same-conversation human approval rule.

The owner MCP Dockerfile is source code only: its Python base is pinned by
digest, server dependencies are locked with hashes, and 48 local synthetic
tests pass. No image build, container launch, or Hermes attachment has been
performed.
