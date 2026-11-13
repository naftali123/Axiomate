"""The shape of a model reply: a list of candidate claims.

The shape is deliberately looser than the claim schema. Any claim field may be
null; what is acceptable is decided afterwards by the claim schema and the
validation gate, never by the reply format.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CandidateFlag(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str
    field: Optional[str] = None
    note: Optional[str] = None


class CandidateAssumption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement: str
    field: Optional[str] = None


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quote: str = Field(min_length=1)
    quote_occurrence: int = 1
    company_cik: Optional[str] = None
    metric: Optional[str] = None
    value_kind: Optional[str] = None
    value_low: Optional[str] = None
    value_high: Optional[str] = None
    stated_value: Optional[str] = None
    stated_scale: Optional[str] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    period_kind: Optional[str] = None
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    basis: Optional[str] = None
    nature: Optional[str] = None
    comparison: Optional[str] = None
    baseline_start: Optional[str] = None
    baseline_end: Optional[str] = None
    polarity: Optional[str] = None
    flags: list[CandidateFlag] = []
    assumptions: list[CandidateAssumption] = []


class Reply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: list[Candidate]
