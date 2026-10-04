"""Trusted, read-only owner facade over the context router.

The host fixes the principal and provider bindings. Agent tool arguments never
contain a sender ID, company scope, credential, bank, SQL query, or URL.
"""

from __future__ import annotations

import json

from .core import ContextRequest, ContextRouter, ContextSourceError, Principal


class OwnerContextService:
    def __init__(self, *, principal: Principal, router: ContextRouter,
                 ledger=None, documents=None, projects=None):
        if principal.scopes != frozenset({'owner'}):
            raise ValueError('the owner facade requires exactly the owner scope')
        self.principal = principal
        self.router = router
        self.ledger = ledger
        self.documents = documents
        self.projects = projects

    @staticmethod
    def _bounded(result: dict, *, max_bytes: int = 24_000) -> dict:
        if len(json.dumps(result, ensure_ascii=False).encode('utf-8')) > max_bytes:
            raise ContextSourceError('context response exceeds the output budget')
        return result

    def status(self) -> dict:
        """Configured means installed in this process, not health-verified."""
        return {
            'scope': 'owner', 'read_only': True,
            'providers': {
                'postgres': 'configured_not_verified' if self.ledger else 'disabled',
                'hindsight': 'configured_not_verified' if self.router.sources['recall'] else 'disabled',
                'openviking': 'configured_not_verified' if self.documents else 'disabled',
                'erp': 'disabled',
            },
            'automatic_retention': False,
            'automatic_audit_writes': False,
        }

    def bundle(self, query: str, *, purpose: str = 'mixed', limit: int = 5,
               max_chars: int = 6_000) -> dict:
        if purpose not in {'mixed', 'memory', 'document'}:
            raise ValueError('business scope is not enabled in the owner facade')
        request = ContextRequest(query, 'owner', purpose, limit, max_chars)
        return self._bounded(self.router.retrieve(request, self.principal))

    def history(self, memory_id: str, *, limit: int = 5) -> dict:
        if self.ledger is None:
            raise ContextSourceError('approved-memory history is unavailable')
        result = self.ledger.history(memory_id, limit)
        if result.get('scope') != 'owner' or result.get('audit_written') is not False:
            raise ContextSourceError('history violated the read-only owner contract')
        rows = result.get('items')
        if not isinstance(rows, list) or len(rows) > limit:
            raise ContextSourceError('history returned an unbounded result')
        bounded = []
        for row in rows:
            if not isinstance(row, dict):
                raise ContextSourceError('history returned an invalid record')
            copy = row.copy()
            for field in ('title', 'body'):
                if field in copy:
                    if not isinstance(copy[field], str):
                        raise ContextSourceError('history text is invalid')
                    copy[field + '_truncated'] = len(copy[field]) > 2_000
                    copy[field] = copy[field][:2_000]
            bounded.append(copy)
        return self._bounded({'items': bounded, 'scope': 'owner', 'audit_written': False})

    def document_read(self, uri: str, *, max_chars: int = 6_000) -> dict:
        if self.documents is None:
            raise ContextSourceError('approved documents are unavailable')
        return self._bounded(self.documents.read('owner', uri, self.principal,
                                                 max_chars).as_dict())

    def project_resolve(self, name: str) -> dict:
        if self.projects is None:
            return {'status': 'unavailable', 'project_id': None,
                    'question': 'Which project do you mean, and what is its source of truth?',
                    'search_status': 'reviewed project registry is not connected'}
        return self._bounded(self.projects.resolve(name, 'owner', self.principal))
