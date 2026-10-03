# Context runtime

This package is a reference library with no startup side effects. Importing
it does not read secrets, write to PostgreSQL, or contact providers.

`core.py` defines `Principal`, `ContextRequest`, `Evidence`, and `ContextRouter`.
`identity.py` maps host-held profile credentials to principals. `projects.py`
keeps infrastructure observations separate from reviewed project mappings and
returns bounded fuzzy suggestions. `lineage.py` calculates authorized impact
from a supplied dependency snapshot. `postgres.py` reads the deployed
owner-only `adam_info` tables. `adapters.py` converts those results and the
Hindsight/OpenViking/ERP contracts into consistent evidence. `manifest.py`
checks approved document versions through a restricted PostgreSQL role.

The read adapters assume a trusted host that supplies credentials and scope.
There is no MCP server or Telegram gateway in this package. The existing bot
and Hermes profiles will connect in a separate integration phase.

```console
python -m unittest discover -s context_runtime -p "test_*.py"
python -m context_runtime.demo
```

The tests and demo use synthetic data. The `postgres` optional dependency is
needed only for a real PostgreSQL connection. A live provider integration must
pin versions and test actual response shapes, permissions and recovery.

`documents.sql` is a proposed migration. Do not apply it without checking
the actual database state and testing restore. `hermes-profile-routes.example.yaml`
is a template with placeholders; it is not active configuration.
