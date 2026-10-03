"""Deterministic, fail-closed retrieval contract for Adam's context sources."""

from .core import ContextAccessError, ContextRequest, ContextRouter, Evidence, Principal

__all__ = ["ContextAccessError", "ContextRequest", "ContextRouter", "Evidence", "Principal"]
