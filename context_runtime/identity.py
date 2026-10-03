"""Resolve profile credentials before invoking any context library method.

The host loads profile-specific credentials from the vault. Never expose this
binding or token input as an agent-callable tool. Gateway routing is a separate
integration boundary and must be tested with real Telegram senders.
"""

import hashlib
import hmac

from .core import ContextAccessError, Principal


class IdentityDirectory:
    def __init__(self, bindings: list[tuple[str, Principal]]):
        self._bindings = []
        seen = set()
        for token, principal in bindings:
            if not isinstance(token, str) or not 32 <= len(token) <= 512 or any(c.isspace() for c in token):
                raise ValueError("profile credentials must be 32-512 non-whitespace characters")
            if not isinstance(principal, Principal):
                raise ValueError("profile principal is required")
            digest = hashlib.sha256(token.encode()).digest()
            if digest in seen:
                raise ValueError("profile credential is reused")
            seen.add(digest)
            self._bindings.append((digest, principal))

    def authenticate(self, token: str) -> Principal:
        if not isinstance(token, str) or not 32 <= len(token) <= 512:
            raise ContextAccessError("invalid context credential")
        digest = hashlib.sha256(token.encode()).digest()
        principal = None
        for expected, candidate in self._bindings:
            if hmac.compare_digest(digest, expected):
                principal = candidate
        if principal is None:
            raise ContextAccessError("invalid context credential")
        return principal
