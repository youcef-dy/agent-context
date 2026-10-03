"""Offline example. Does not read .env or connect to a provider."""

import hashlib
import json

from .core import ContextRequest, ContextRouter, Evidence, Principal
from .projects import Project, ProjectCatalog


def main():
    principal = Principal("demo-user", frozenset({"owner"}), "synthetic-demo")
    body = "For the demo project, prepare a concise progress report."

    class SyntheticLedger:
        def search(self, request, actor):
            return [Evidence("ledger", "owner", "demo:rule-1", "demo://message/1",
                             hashlib.sha256(body.encode()).hexdigest(), body,
                             "2026-01-01T10:00:00Z", "2026-01-01T10:05:00Z", "1")]

    catalog = ProjectCatalog([Project("demo", "Demo project", "owner", ("demo",),
                                      "demo-user", "2026-01-01T10:00:00Z")])
    result = ContextRouter(ledger=SyntheticLedger()).retrieve(
        ContextRequest("progress report", "owner", purpose="memory"), principal)
    print(json.dumps({"mode": "offline-synthetic", "project": catalog.resolve(
        "demo", "owner", principal), "context": result}, indent=2))


if __name__ == "__main__":
    main()
