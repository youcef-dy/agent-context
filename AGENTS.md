# Repository Guidelines

## Purpose and structure

This repository owns Adam's context architecture and retrieval foundation.
Keep architecture, source decisions, contracts, and rollout status in `docs/`.
Python library code and synthetic unit tests live in `context_runtime/`.
The interactive diagram is generated from `docs/context-architecture.json`.
Update its source and regenerate the HTML together.

## Development and validation

Use Python 3.11 or newer. Run `python -m unittest discover -s context_runtime
-p "test_*.py"` from the root, then `python -m context_runtime.demo` for the
offline example. Base tests require no network, credentials, or live database.
Install the optional `postgres` extra only for PostgreSQL integration work.
Verify Markdown links and parse JSON changes before committing.

## Style and contracts

Use four-space Python indentation, type annotations for public contracts,
snake_case functions, and descriptive `test_*.py` files. Use two-space JSON
indentation and stable diagram IDs. Prefer small explicit adapters over a new
agent framework. Preserve source IDs, versions, timestamps, scope, and
uncertainty in returned evidence. Changes to authorization, retrieval order,
expiry, deduplication, or provider fallback need behavioral regression tests.

## Data and access boundaries

Never commit credentials, `.env` files, chat exports, real customer records,
or production database dumps. Examples must use synthetic identities.
Identity and allowed scope come from trusted host configuration, never a
model-supplied claim. Reads do not silently write an audit record. Preserve the
existing same-conversation approval requirement for Render and PostgreSQL
writes. Do not apply migrations or deploy providers as part of a code change.

## Commits and reviews

Use scoped imperative subjects such as `feat: bound cross-source retrieval`.
Keep commits focused. Describe the behavior, tests, remaining limitations, and
deployment implications. Distinguish implemented, simulated, and live-tested
capabilities; never describe a contract or mock as a working integration.
