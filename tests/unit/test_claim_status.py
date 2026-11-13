"""Derivation of the formalization status (task T020)."""
import pytest

from axiomate.claims.status import derive_status

OPEN = {"reason": "vague_quantity", "field": "value_low", "resolved": False}
CLOSED = {"reason": "underspecified_time", "field": "period_start", "resolved": True}
ASSUMED = {"statement": "the year is 2024", "field": "period_start", "origin": "human"}


@pytest.mark.parametrize("flags, assumptions, expected", [
    ([], [], "formal"),
    ([], [ASSUMED], "formal-with-assumptions"),
    ([CLOSED], [], "formal"),
    ([CLOSED], [ASSUMED], "formal-with-assumptions"),
    ([OPEN], [], "not-formalizable"),
    ([OPEN], [ASSUMED], "not-formalizable"),
    ([CLOSED, OPEN], [ASSUMED, ASSUMED], "not-formalizable"),
])
def test_status_follows_the_three_rules_in_order(flags, assumptions, expected):
    assert derive_status(flags, assumptions) == expected
