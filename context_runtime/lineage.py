"""Compute authorized downstream impact from a reviewed artifact snapshot."""

from dataclasses import dataclass

from .core import ContextAccessError, Principal


@dataclass(frozen=True, order=True)
class ArtifactRef:
    scope: str
    artifact_id: str
    version: str
    selector: str = "*"

    def __post_init__(self):
        if any(not isinstance(value, str) or not 1 <= len(value) <= 200
               for value in (self.scope, self.artifact_id, self.version, self.selector)):
            raise ValueError("artifact reference is incomplete")


@dataclass(frozen=True)
class Dependency:
    upstream: ArtifactRef
    downstream: ArtifactRef

    def __post_init__(self):
        if self.upstream.scope != self.downstream.scope:
            raise ValueError("cross-scope artifact links need a separate reviewed sharing contract")


def affected_artifacts(changed: ArtifactRef, links: list[Dependency], principal: Principal,
                       *, max_results: int = 100) -> dict:
    if changed.scope not in principal.scopes:
        raise ContextAccessError("actor is not authorized for artifact scope")
    if type(max_results) is not int or not 1 <= max_results <= 1000:
        raise ValueError("invalid impact budget")
    if len(links) > 10000:
        raise ValueError("dependency snapshot exceeds budget")
    seen = {changed}
    frontier = [changed]
    affected = set()
    while frontier:
        current = frontier.pop()
        for link in links:
            source, target = link.upstream, link.downstream
            if source.scope != changed.scope or target.scope != changed.scope:
                continue
            same_version = (source.artifact_id, source.version) == (current.artifact_id, current.version)
            selector_matches = current.selector == "*" or source.selector == "*" or current.selector == source.selector
            if not same_version or not selector_matches or target in seen:
                continue
            if len(affected) >= max_results:
                return {"affected": sorted(affected), "truncated": True}
            seen.add(target)
            affected.add(target)
            frontier.append(target)
    return {"affected": sorted(affected), "truncated": False}
