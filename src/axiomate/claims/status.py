"""Derivation of a claim's formalization status. The status is never chosen."""
from __future__ import annotations

from typing import Any, Iterable

FORMAL = "formal"
FORMAL_WITH_ASSUMPTIONS = "formal-with-assumptions"
NOT_FORMALIZABLE = "not-formalizable"
STATUSES = (FORMAL, FORMAL_WITH_ASSUMPTIONS, NOT_FORMALIZABLE)


def _resolved(flag: Any) -> bool:
    return flag["resolved"] if isinstance(flag, dict) else flag.resolved


def derive_status(flags: Iterable[Any], assumptions: Iterable[Any]) -> str:
    """Any unresolved flag: not formalizable. Otherwise any assumption: formal with assumptions."""
    if any(not _resolved(flag) for flag in flags):
        return NOT_FORMALIZABLE
    if list(assumptions):
        return FORMAL_WITH_ASSUMPTIONS
    return FORMAL
