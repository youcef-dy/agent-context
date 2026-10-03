"""Read-only source adapters. No agent-facing SQL, ingest, or approval tools."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import hashlib
import re
from typing import Callable, Protocol
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener
import ssl

from .core import (ContextAccessError, ContextRequest, ContextSourceError, Evidence,
                   Principal, utc_timestamp)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


class JsonHttp:
    """Fixed-base HTTPS client; loopback HTTP is allowed for a private pilot."""

    def __init__(self, base_url: str, api_key: str, *, transport=None):
        parsed = urlsplit(base_url)
        loopback = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
        if not (parsed.scheme == "https" or loopback) or not parsed.hostname or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("context service URL must be HTTPS or loopback HTTP origin")
        if not api_key or "\n" in api_key or "\r" in api_key:
            raise ValueError("service token is required")
        self.base_url, self.api_key = base_url.rstrip("/"), api_key
        self.transport = transport or build_opener(ProxyHandler({}), NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))

    def _read_json(self, request: Request) -> dict:
        try:
            with self.transport.open(request, timeout=10) as response:
                raw = response.read(65537)
                if response.status != 200 or len(raw) > 65536:
                    raise ContextSourceError("context source returned invalid status or size")
        except HTTPError:
            raise ContextSourceError("context source rejected the request") from None
        except (TimeoutError, OSError):
            raise ContextSourceError("context source is unavailable") from None
        try:
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError()
            return result
        except (ValueError, UnicodeDecodeError):
            raise ContextSourceError("context source returned invalid JSON") from None

    def post(self, path: str, payload: dict) -> dict:
        if path not in {"/api/v1/search/find", "/adam/context/search"} and not re.fullmatch(
                r"/v1/default/banks/[A-Za-z0-9_-]{1,100}/memories/recall", path):
            raise ValueError("unreviewed context endpoint")
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        if len(body) > 4096:
            raise ValueError("context request too large")
        request = Request(self.base_url + path, data=body, method="POST", headers={
            "Authorization": "Bearer " + self.api_key, "Content-Type": "application/json",
            "Accept": "application/json"})
        return self._read_json(request)

    def get(self, path: str, params: dict[str, str]) -> dict:
        if path != "/api/v1/content/read" or set(params) != {"uri"}:
            raise ValueError("unreviewed context read endpoint")
        request = Request(self.base_url + path + "?" + urlencode(params), method="GET", headers={
            "Authorization": "Bearer " + self.api_key, "Accept": "application/json"})
        return self._read_json(request)


class LedgerSource:
    """Adapter over the deployed owner-only ContextCore read method."""

    def __init__(self, core):
        self.core = core

    def search(self, request: ContextRequest, principal: Principal) -> list[Evidence]:
        if request.scope not in principal.scopes:
            raise ContextAccessError("actor is not authorized for requested scope")
        if request.scope != "owner":
            return []  # The deployed Adam ledger has owner-only RLS.
        data = self.core.search(request.query, min(request.limit, 10))
        return [Evidence(
            kind="ledger", scope="owner", canonical_id="memory:" + row["memory_id"],
            source_uri=row["source_uri"], content_hash=row["content_hash"],
            content=row["title"] + "\n" + row["body"], observed_at=row["observed_at"],
            recorded_at=row["recorded_at"], version=str(row["revision"]),
            expires_at=row.get("expires_at")) for row in data["items"]]


class ErpSource:
    """Calls an ERP-owned endpoint with a user-bound token from trusted code.

    The endpoint must independently check actor/company authorization. This
    adapter is not usable until the ERP implements that contract.
    """

    def __init__(self, origin: str, token_for_actor: Callable[[Principal], str], *, transport_factory=JsonHttp):
        self.origin, self.token_for_actor, self.transport_factory = origin, token_for_actor, transport_factory

    def search(self, request: ContextRequest, principal: Principal) -> list[Evidence]:
        if request.scope not in principal.scopes:
            raise ContextAccessError("actor is not authorized for requested scope")
        if not request.scope.startswith("company:"):
            return []
        token = self.token_for_actor(principal)
        if not token:
            raise ContextAccessError("ERP user-bound credential unavailable")
        company_id = request.scope.partition(":")[2]
        response = self.transport_factory(self.origin, token).post("/adam/context/search", {
            "company_id": company_id, "query": request.query, "limit": request.limit})
        records = response.get("records")
        if not isinstance(records, list) or len(records) > request.limit:
            raise ContextSourceError("ERP response is unbounded")
        evidence = []
        for row in records:
            if not isinstance(row, dict) or row.get("company_id") != company_id:
                raise ContextAccessError("ERP returned a record from another company")
            evidence.append(Evidence(
                kind="erp", scope=request.scope,
                canonical_id="erp:" + str(row["record_id"]),
                source_uri=str(row["source_uri"]), content_hash=str(row["content_hash"]),
                content=str(row["summary"]), observed_at=str(row["updated_at"]),
                recorded_at=str(row["updated_at"]), version=str(row["revision"])))
        return evidence


@dataclass(frozen=True)
class DocumentManifest:
    """Approved source-of-truth metadata, independent of OpenViking's index."""

    viking_uri: str
    scope: str
    source_uri: str
    content_hash: str
    version: str
    observed_at: str
    approved_at: str
    expires_at: str | None = None
    indexed_text_hash: str | None = None


class ManifestStore(Protocol):
    def approved(self, scope: str, uri: str) -> DocumentManifest | None: ...


class OpenVikingSource:
    """Search approved L2 resource files; index hits never grant access."""

    def __init__(self, client: JsonHttp, manifest: ManifestStore, scope_prefixes: dict[str, str]):
        self.client, self.manifest = client, manifest
        self.scope_prefixes = scope_prefixes.copy()
        for scope, prefix in self.scope_prefixes.items():
            if not prefix.startswith("viking://resources/") or not prefix.endswith("/"):
                raise ValueError("OpenViking scope must be a resource directory")

    def search(self, request: ContextRequest, principal: Principal) -> list[Evidence]:
        if request.scope not in principal.scopes:
            raise ContextAccessError("actor is not authorized for requested scope")
        prefix = self.scope_prefixes.get(request.scope)
        if prefix is None:
            return []
        response = self.client.post("/api/v1/search/find", {
            "query": request.query, "target_uri": prefix, "context_type": "resource",
            "level": 2, "limit": min(request.limit * 2, 20)})
        resources = response.get("result", {}).get("resources")
        if not isinstance(resources, list) or len(resources) > 20:
            raise ContextSourceError("OpenViking result is unbounded")
        evidence = []
        for hit in resources:
            if not isinstance(hit, dict) or not isinstance(hit.get("uri"), str):
                raise ContextSourceError("OpenViking returned an invalid hit")
            uri = hit["uri"]
            if not uri.startswith(prefix) or hit.get("level") != 2:
                continue
            document = self.manifest.approved(request.scope, uri)
            if document is None:
                continue
            if document.scope != request.scope or document.viking_uri != uri:
                raise ContextAccessError("document manifest scope mismatch")
            if document.expires_at and datetime.fromisoformat(utc_timestamp(document.expires_at)) <= datetime.now(timezone.utc):
                continue
            abstract = hit.get("abstract")
            if not isinstance(abstract, str) or not abstract.strip():
                continue
            evidence.append(Evidence(
                kind="document", scope=request.scope, canonical_id="document:" + document.source_uri,
                source_uri=document.source_uri, content_hash=document.content_hash,
                content=abstract[:3000], observed_at=document.observed_at,
                recorded_at=document.approved_at, version=document.version,
                expires_at=document.expires_at,
                excerpt_truncated=len(abstract) > 3000))
            if len(evidence) == request.limit:
                break
        return evidence

    def read(self, scope: str, uri: str, principal: Principal, max_chars: int = 6000) -> Evidence:
        """Load L2 only after rechecking the current approved manifest."""
        if scope not in principal.scopes:
            raise ContextAccessError("actor is not authorized for document scope")
        if type(max_chars) is not int or not 500 <= max_chars <= 10000:
            raise ValueError("invalid document read budget")
        prefix = self.scope_prefixes.get(scope)
        if not prefix or not uri.startswith(prefix):
            raise ContextAccessError("document URI is outside the authorized collection")
        document = self.manifest.approved(scope, uri)
        if document is None or document.scope != scope or document.viking_uri != uri:
            raise ContextAccessError("document is not currently approved")
        if document.expires_at and datetime.fromisoformat(utc_timestamp(document.expires_at)) <= datetime.now(timezone.utc):
            raise ContextAccessError("document approval expired")
        result = self.client.get("/api/v1/content/read", {"uri": uri}).get("result")
        content = result if isinstance(result, str) else result.get("content") if isinstance(result, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ContextSourceError("document content is unavailable")
        if not document.indexed_text_hash or hashlib.sha256(content.encode("utf-8")).hexdigest() != document.indexed_text_hash:
            raise ContextSourceError("document text does not match the approved indexed version")
        return Evidence(
            kind="document", scope=scope, canonical_id="document:" + document.source_uri,
            source_uri=document.source_uri, content_hash=document.content_hash,
            content=content[:max_chars], observed_at=document.observed_at,
            recorded_at=document.approved_at, version=document.version,
            expires_at=document.expires_at,
            excerpt_truncated=len(content) > max_chars).checked(scope, "document")


class HindsightSource:
    """Read-only personal recall; bank selection is trusted host configuration.

    Uses the documented recall API. Text hashes identify the retrieved memory
    snapshot, not the original conversation. No retain or reflect call occurs.
    """

    def __init__(self, client: JsonHttp, bank_for_actor: Callable[[Principal], str]):
        self.client, self.bank_for_actor = client, bank_for_actor

    def search(self, request: ContextRequest, principal: Principal) -> list[Evidence]:
        if request.scope not in principal.scopes:
            raise ContextAccessError("actor is not authorized for requested scope")
        if request.scope != "owner":
            return []
        bank = self.bank_for_actor(principal)
        if not isinstance(bank, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", bank):
            raise ContextAccessError("personal memory bank is not configured")
        response = self.client.post(f"/v1/default/banks/{bank}/memories/recall", {
            "query": request.query, "types": ["world", "experience"],
            "budget": "low", "max_tokens": 2048})
        records = response.get("results")
        if not isinstance(records, list) or len(records) > 200:
            raise ContextSourceError("Hindsight returned an invalid result")
        evidence = []
        for row in records[:request.limit]:
            if not isinstance(row, dict):
                raise ContextSourceError("Hindsight returned an invalid memory")
            text, memory_id = row.get("text"), row.get("id")
            if not isinstance(text, str) or not text.strip() or not isinstance(memory_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", memory_id):
                raise ContextSourceError("Hindsight memory provenance is incomplete")
            recorded = utc_timestamp(row.get("mentioned_at"))
            occurred = utc_timestamp(row.get("occurred_start") or recorded)
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            evidence.append(Evidence(
                kind="recall", scope="owner", canonical_id=f"hindsight:{bank}:{memory_id}",
                source_uri=f"hindsight://{bank}/memories/{memory_id}",
                content_hash=digest, content=text, observed_at=occurred,
                recorded_at=recorded, version=digest))
        return evidence
