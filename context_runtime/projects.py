"""Project discovery and clarification; observations are not project facts.

Only a reviewed mapping can identify a project. Render service names, repository
names, and other infrastructure observations may be shown as candidate labels,
but can never silently create or confirm a project.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import unicodedata

from .core import ContextAccessError, Principal, utc_timestamp


REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")


def _label(value: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 120:
        raise ValueError("project label must contain 1-120 characters")
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w]+", " ", normalized).split())


@dataclass(frozen=True)
class Project:
    project_id: str
    name: str
    scope: str
    aliases: tuple[str, ...]
    confirmed_by: str
    confirmed_at: str

    def __post_init__(self) -> None:
        if not REF.fullmatch(self.project_id):
            raise ValueError("invalid project identifier")
        _label(self.name)
        if not self.scope or not self.confirmed_by:
            raise ValueError("project scope and reviewer are required")
        utc_timestamp(self.confirmed_at)
        for alias in self.aliases:
            _label(alias)


@dataclass(frozen=True)
class ObservedResource:
    """Read-only source inventory item, never an authorization grant."""

    provider: str
    external_id: str
    label: str
    scope: str
    observed_at: str

    def __post_init__(self) -> None:
        if not REF.fullmatch(self.provider) or not self.external_id:
            raise ValueError("invalid resource identity")
        _label(self.label)
        utc_timestamp(self.observed_at)


class ProjectCatalog:
    """Resolve only confirmed, scope-matched names; otherwise ask the user."""

    def __init__(self, projects: list[Project], observations: list[ObservedResource] | None = None):
        self.projects = tuple(projects)
        self.observations = tuple(observations or ())
        if len({(p.scope, p.project_id) for p in self.projects}) != len(self.projects):
            raise ValueError("duplicate scoped project identifier")

    def resolve(self, name: str, scope: str, principal: Principal) -> dict:
        if scope not in principal.scopes:
            raise ContextAccessError("actor is not authorized for requested scope")
        key = _label(name)
        matches = [p for p in self.projects if p.scope == scope and
                   key in {_label(p.name), *(_label(alias) for alias in p.aliases)}]
        if len(matches) == 1:
            project = matches[0]
            return {"status": "confirmed", "project_id": project.project_id,
                    "name": project.name, "scope": scope,
                    "confirmed_by": project.confirmed_by,
                    "confirmed_at": project.confirmed_at}
        if len(matches) > 1:
            return {"status": "ambiguous", "project_id": None,
                    "question": "Which project do you mean?",
                    "candidates": sorted({p.name for p in matches})[:5]}
        # Exact observed names can help formulate a question, but do not
        # establish that the resource represents the user's project.
        candidates = sorted({o.label for o in self.observations
                             if o.scope == scope and _label(o.label) == key})[:5]
        suggestions = []
        for project in self.projects:
            if project.scope != scope:
                continue
            similarity = max(SequenceMatcher(None, key, _label(label)).ratio()
                             for label in (project.name, *project.aliases))
            if similarity >= 0.6:
                suggestions.append({"project_id": project.project_id, "name": project.name,
                                    "similarity": round(similarity, 3)})
        suggestions.sort(key=lambda candidate: (-candidate["similarity"], candidate["project_id"]))
        return {"status": "unknown", "project_id": None,
                "question": "Which project do you mean, and what should I use as its source of truth?",
                "observed_resource_labels": candidates,
                "suggested_projects": suggestions[:5],
                "search_status": "catalog_only; search authorized history and semantic sources before asking"}
