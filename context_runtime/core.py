"""Bounded context routing. Call only from a service with verified identity.

This module is intentionally not an MCP server. An LLM must never be allowed to
construct Principal or choose another user's scope through tool arguments.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Protocol
import hashlib
import re


SCOPE = re.compile(r"^(owner|company:[a-zA-Z0-9_-]{1,64})$")
HASH = re.compile(r"^[a-f0-9]{64}$")


class ContextAccessError(ValueError):
    """Missing or inconsistent trusted scope; no partial result is returned."""


class ContextSourceError(RuntimeError):
    """A source failed or returned an invalid contract."""


def utc_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.astimezone(timezone.utc).isoformat()
    except (ValueError, AttributeError):
        raise ContextSourceError("source timestamp is missing or invalid") from None


@dataclass(frozen=True)
class Principal:
    """Created by a trusted host after authentication, never by Hermes text."""

    actor_id: str
    scopes: frozenset[str]
    issuer: str

    def __post_init__(self) -> None:
        if not self.actor_id or not self.issuer or not self.scopes:
            raise ContextAccessError("verified actor and issuer are required")
        if any(not SCOPE.fullmatch(scope) for scope in self.scopes):
            raise ContextAccessError("invalid granted scope")


@dataclass(frozen=True)
class ContextRequest:
    query: str
    scope: str
    purpose: str = "mixed"
    limit: int = 8
    max_chars: int = 8000

    def __post_init__(self) -> None:
        if not SCOPE.fullmatch(self.scope):
            raise ContextAccessError("invalid requested scope")
        if not isinstance(self.query, str) or not 1 <= len(self.query.strip()) <= 300:
            raise ValueError("query must contain 1-300 characters")
        if self.purpose not in {"business", "memory", "document", "mixed"}:
            raise ValueError("unsupported retrieval purpose")
        if type(self.limit) is not int or not 1 <= self.limit <= 20:
            raise ValueError("limit must be 1-20")
        if type(self.max_chars) is not int or not 500 <= self.max_chars <= 20000:
            raise ValueError("max_chars must be 500-20000")


@dataclass(frozen=True)
class Evidence:
    kind: str
    scope: str
    canonical_id: str
    source_uri: str
    content_hash: str
    content: str
    observed_at: str
    recorded_at: str
    version: str
    expires_at: str | None = None
    excerpt_truncated: bool = False

    def checked(self, requested_scope: str, expected_kind: str) -> "Evidence":
        if self.kind != expected_kind or self.scope != requested_scope:
            raise ContextAccessError("source returned evidence outside the authorized scope")
        if not self.canonical_id or not self.source_uri or not self.version:
            raise ContextSourceError("evidence has incomplete provenance")
        if not HASH.fullmatch(self.content_hash):
            raise ContextSourceError("evidence has an invalid source hash")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ContextSourceError("evidence has no content")
        utc_timestamp(self.observed_at)
        utc_timestamp(self.recorded_at)
        if self.expires_at and datetime.fromisoformat(utc_timestamp(self.expires_at)) <= datetime.now(timezone.utc):
            raise ContextSourceError("expired evidence returned by source")
        return self

    def as_dict(self) -> dict:
        return {
            "kind": self.kind, "scope": self.scope, "canonical_id": self.canonical_id,
            "source_uri": self.source_uri, "content_hash": self.content_hash,
            "content": self.content, "observed_at": self.observed_at,
            "excerpt_hash": hashlib.sha256(self.content.encode("utf-8")).hexdigest(),
            "recorded_at": self.recorded_at, "version": self.version,
            "expires_at": self.expires_at, "excerpt_truncated": self.excerpt_truncated,
            "untrusted_source_text": True,
        }


class Source(Protocol):
    def search(self, request: ContextRequest, principal: Principal) -> list[Evidence]: ...


class ContextRouter:
    """ERP outranks caches; company-scope ERP failure blocks all company answers."""

    def __init__(self, *, erp: Source | None = None, ledger: Source | None = None,
                 documents: Source | None = None, recall: Source | None = None):
        self.sources = {"erp": erp, "ledger": ledger, "document": documents, "recall": recall}

    def retrieve(self, request: ContextRequest, principal: Principal) -> dict:
        if request.scope not in principal.scopes:
            raise ContextAccessError("actor is not authorized for requested scope")
        company = request.scope.startswith("company:")
        if company and request.purpose == "memory":
            return self._unavailable("company conversational memory is not enabled")
        required_erp = company and request.purpose in {"business", "mixed"}
        if request.purpose == "business":
            order = ("erp",)
        elif request.purpose == "document":
            order = ("document",)
        elif request.purpose == "memory":
            order = ("ledger", "recall")
        else:
            order = ("erp", "ledger", "document", "recall") if company else ("ledger", "document", "recall")

        gathered: list[Evidence] = []
        warnings: list[str] = []
        for name in order:
            if company and name == "recall":
                continue  # Personal recall is never a fallback for company data.
            source = self.sources[name]
            if source is None:
                if name == "erp" and required_erp:
                    return self._unavailable("live ERP adapter is not configured")
                continue
            try:
                candidates = source.search(request, principal)
                if not isinstance(candidates, list) or len(candidates) > 2 * request.limit:
                    raise ContextSourceError("source returned an unbounded result")
                if any(not isinstance(item, Evidence) for item in candidates):
                    raise ContextSourceError("source returned an invalid evidence item")
                checked = [item.checked(request.scope, name) for item in candidates]
                gathered.extend(checked)  # Reject a bad batch atomically.
            except ContextAccessError:
                raise
            except ContextSourceError:
                if name == "erp" and required_erp:
                    return self._unavailable("live ERP read failed or returned invalid scope")
                warnings.append(f"{name} returned invalid or unavailable evidence")
            except Exception:
                if name == "erp" and required_erp:
                    return self._unavailable("live ERP read is unavailable")
                warnings.append(f"{name} unavailable; results may be incomplete")

        # The adapter call order is the authority order. Exact duplicate evidence
        # collapses; differing versions of the same canonical source remain visible.
        seen: set[tuple[str, str]] = set()
        hashes: dict[str, set[str]] = {}
        chosen: list[Evidence] = []
        remaining = request.max_chars
        for item in gathered:
            identity = (item.canonical_id, item.content_hash)
            if identity in seen or len(chosen) == request.limit or remaining == 0:
                continue
            seen.add(identity)
            hashes.setdefault(item.canonical_id, set()).add(item.content_hash)
            excerpt = item.content[:remaining]
            chosen.append(replace(item, content=excerpt,
                                  excerpt_truncated=item.excerpt_truncated or len(excerpt) < len(item.content)))
            remaining -= len(excerpt)
        return {
            "items": [item.as_dict() for item in chosen],
            "conflicts": sorted(key for key, values in hashes.items() if len(values) > 1),
            "warnings": warnings, "answerable": bool(chosen),
            "live_erp_checked": "erp" in order and self.sources["erp"] is not None,
            "query_hash": hashlib.sha256(request.query.encode("utf-8")).hexdigest(),
            "queried_at": datetime.now(timezone.utc).isoformat(),
            "policy": "ERP > approved ledger > approved documents > low-trust recall",
        }

    @staticmethod
    def _unavailable(reason: str) -> dict:
        return {"items": [], "conflicts": [], "warnings": [reason], "answerable": False,
                "live_erp_checked": False, "queried_at": datetime.now(timezone.utc).isoformat(),
                "policy": "live business facts require a successful authorized ERP read"}
