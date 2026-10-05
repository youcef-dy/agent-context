# Production rollout checkpoint — 2026-10-05

Work is paused at the owner's request. This is a handoff record, **not** a
production-readiness declaration. Commit `10e04d3` was the prior tested
read-only baseline. The staging changes listed below are saved with this
checkpoint but still need build and live review. Do not resize the VPS, buy a Render service, enable retention, or
ingest real documents merely because this checkpoint exists.

## Decisions to preserve

- One human owner uses two allowlisted Telegram IDs on the existing bot.
  `gateway.profile_routes` has zero entries; both use the default profile.
- Hindsight automatic retention remains **off**. Only explicit synthetic-bank
  tests are authorized. Do not enable a native memory plugin with default
  retention or a second duplicate recall path.
- OpenViking's first corpus is synthetic only. The owner confirmed **no real
  documents yet**; no real directory or source has been approved for ingest.
- A possible 8 GiB VPS upgrade was discussed, not authorized. The owner asked
  to check available Hetzner credit first. No paid Render service was approved.

## Verified live state

- VPS SSH over the existing VPN worked. Hermes, `adam-hindsight`, and
  `adam-render-broker` were running; no OpenViking or context MCP container was
  running. Hermes has no active Hindsight memory provider and its MCP config
  names only the existing PostgreSQL and Render servers.
- The VPS showed 3,810 MiB RAM total, about 2,679 MiB available, 631 MiB swap
  used, and 40 GiB free on the 75 GiB root filesystem. These are momentary
  readings, **not** OpenViking peak-capacity evidence. Hermes has a 3 GiB
  container memory limit; Hindsight has a 2,250 MiB limit; the broker has
  256 MiB. Their limits cannot all be consumed simultaneously on this host.
- The encrypted essential GitHub backup timer was active and the latest
  service result was successful. Its Hindsight ZIP has passed download/hash
  and archive-integrity checks, but **no fresh isolated Hindsight restore** has
  been performed. Render PostgreSQL is outside that backup.
- Read-only recall of the dedicated synthetic Hindsight bank returned HTTP
  200 and one result. A value-silent contract audit found `id`, `text`, and
  `mentioned_at`; `occurred_start` was absent, which the adapter handles by
  using `mentioned_at`. No real memory text or credential was printed.
- The two Telegram IDs were counted in the allowlist without displaying them.
  A denied third sender/group test has **not** been performed. The earlier
  substring-based route audit was misleading; the parsed route count is zero.
- Existing `adam_info` PostgreSQL reads and Render MCP reads were verified in
  the preceding pass, not re-tested during this checkpoint pass.

## Repository state at pause

The repository contains the bounded read-only owner facade, Hindsight recall
adapter, OpenViking approved-manifest adapter, and plan. This checkpoint also
saves **not-yet-deployed** staging changes: `Dockerfile`, `.dockerignore`,
`context_runtime/serve.py`, `context_runtime/test_service.py`,
`docs/operations.md`, and `ops/audit_hindsight_recall_contract.py`. They add
container packaging, a private-file PostgreSQL DSN option, and a value-silent
synthetic recall audit. All **47 synthetic/local tests pass** after those
changes. No Docker image was built and no context MCP service was deployed.

## Next controlled sequence

1. Review the saved staging changes; build the image and validate its
   dependencies and resource use without attaching it to Hermes.
2. Restore the encrypted off-host Hindsight export into a **fresh isolated**
   instance; verify synthetic recall and deletion there, then remove only the
   explicitly named test instance and volume. Never restore over the live bank.
3. Test both owner Telegram IDs plus denial of a third ID and group. Stage the
   bearer-authenticated context MCP privately, prove restricted `adam_reader`
   access and no audit/write tools, then attach it to Hermes and test restart.
4. Check Hetzner Accounts → Invoice → Credit and Hetzner Console → Usage.
   No Hetzner API credential or authenticated browser session was available in
   this pass, so **credit and resize price were not verified**. Obtain a clear
   resize decision before any paid capacity change.
5. On a measured safe host, deploy a pinned OpenViking service with persistent
   storage and a non-root data key; ingest **synthetic documents only**.
   Verify index completion, approved-manifest filtering, hash-checked detail,
   revocation, restart, backup/restore, and peak memory. Do not connect a real
   corpus until its exact source and retention policy are approved.
6. Separately verify Render PostgreSQL recovery, then exercise the complete
   Telegram → retrieval → cited answer → restart path. Do not mark the
   three-component layer production-ready until these acceptance results are
   recorded in `docs/production-status.md`.

Relevant design and gates: [implementation plan](implementation-plan.md),
[current status](production-status.md), and [operations](operations.md).
