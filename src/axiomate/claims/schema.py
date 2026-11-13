"""The claim schema: what a submitted claim must look like before it is grounded.

`parse_claim` checks one submitted claim and returns it in stored form, or
raises an AxiomateError naming the first offending field:

- `schema_invalid`: a field is absent, of the wrong type, outside its list of
  values, or contradicts another field;
- `unknown_metric`: the metric is a name outside the fixed list;
- `empty_field_without_flag`: a field is empty and no unresolved flag covers it.

Empty fields (FR-017). Every field must be present in the submission; a field
the text does not support is given as null, and an unresolved flag must name
it. Fields that describe one thing are covered together: a flag on any field of
the value (kind, low, high, stated value, scale, unit, currency) covers all of
them, and likewise for the period and for the baseline.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Literal, Optional

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, StrictBool, StrictInt, StrictStr
from pydantic import ValidationError

from axiomate.claims.status import STATUSES
from axiomate.errors import AxiomateError

SCHEMA_VERSION = "1"

METRICS = ("revenue", "net_income", "earnings_per_share", "operating_cash_flow")
FLAG_REASONS = (
    "unresolved_reference", "underspecified_time", "vague_quantity", "implicit_scope", "unmapped_metric",
    "missing_background", "hedged_or_conditional", "reported_speech", "figurative", "opinion",
)
ORIGINS = ("context_store", "model", "human")

_NUMBER = re.compile(r"-?(?:\d+(?:\.\d+)?|\.\d+)")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _decimal(value: Any) -> Any:
    """Exact decimal in one plain form; floats are refused because they are inexact."""
    if value is None:
        return None
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError("give the number as text or as a whole number, not as a float")
    if isinstance(value, (int, Decimal)):
        value = format(value, "f") if isinstance(value, Decimal) else str(value)
    if not isinstance(value, str) or not _NUMBER.fullmatch(value):
        raise ValueError("must be a plain decimal number such as 1800000 or 1.72")
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError("must be a plain decimal number") from None
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def _iso_date(value: str) -> str:
    if not _ISO_DATE.fullmatch(value):
        raise ValueError("must be a date written YYYY-MM-DD")
    date.fromisoformat(value)
    return value


def _claim_field(value: Optional[str]) -> Optional[str]:
    if value is not None and value not in CONTENT_FIELDS:
        raise ValueError("must name a field of the claim")
    return value


Number = Annotated[Optional[StrictStr], BeforeValidator(_decimal)]
Day = Annotated[StrictStr, AfterValidator(_iso_date)]
FieldName = Annotated[Optional[StrictStr], AfterValidator(_claim_field)]
_STRICT = ConfigDict(extra="forbid", frozen=True)


class Flag(BaseModel):
    model_config = _STRICT
    reason: Literal[FLAG_REASONS]  # type: ignore[valid-type]
    field: FieldName = None
    resolved: StrictBool
    note: Optional[StrictStr] = None


class Assumption(BaseModel):
    model_config = _STRICT
    statement: Annotated[StrictStr, Field(min_length=1)]
    field: FieldName = None
    origin: Literal[ORIGINS]  # type: ignore[valid-type]


class Claim(BaseModel):
    model_config = _STRICT
    company_cik: Optional[Annotated[StrictStr, Field(pattern=r"^\d{10}$")]]
    metric: Optional[StrictStr]
    value_kind: Optional[Literal["exact", "approximate", "at_least", "at_most", "range"]]
    value_low: Number
    value_high: Number
    stated_value: Number
    stated_scale: Optional[Literal["units", "thousands", "millions", "billions"]]
    unit: Optional[Literal["currency", "currency_per_share", "percent"]]
    currency: Optional[Annotated[StrictStr, Field(pattern=r"^[A-Z]{3}$")]]
    period_kind: Optional[Literal["duration", "instant"]]
    fiscal_year: Optional[Annotated[StrictInt, Field(ge=1900, le=2100)]]
    fiscal_period: Optional[Literal["Q1", "Q2", "Q3", "Q4", "H1", "9M", "FY"]]
    period_start: Optional[Day]
    period_end: Optional[Day]
    basis: Optional[Literal["reported", "adjusted"]]
    nature: Optional[Literal["actual", "guidance", "forecast"]]
    comparison: Optional[Literal["absolute", "change_vs_period"]]
    baseline_start: Optional[Day]
    baseline_end: Optional[Day]
    polarity: Optional[Literal["affirmed", "denied"]]
    document_id: Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
    segment_index: Optional[Annotated[StrictInt, Field(ge=0)]] = None
    span_start: Annotated[StrictInt, Field(ge=0)]
    span_end: Annotated[StrictInt, Field(ge=1)]
    quote: Annotated[StrictStr, Field(min_length=1)]
    said_on: Day
    status: Optional[Literal[STATUSES]] = None  # type: ignore[valid-type]
    flags: list[Flag] = []
    assumptions: list[Assumption] = []


# Fields that say what the claim asserts, grouped by what one flag can cover.
GROUPS: tuple[tuple[str, ...], ...] = (
    ("company_cik",), ("metric",),
    ("value_kind", "value_low", "value_high", "stated_value", "stated_scale", "unit", "currency"),
    ("period_kind", "fiscal_year", "fiscal_period", "period_start", "period_end"),
    ("basis",), ("nature",), ("comparison",),
    ("baseline_start", "baseline_end"),
    ("polarity",),
)
CONTENT_FIELDS = tuple(name for group in GROUPS for name in group)
_GROUP_OF = {name: group for group in GROUPS for name in group}


def _invalid(field: Optional[str], message: str) -> AxiomateError:
    return AxiomateError("schema_invalid", message, field)


def _field_name(location: tuple) -> Optional[str]:
    name = ""
    for part in location:
        name += f"[{part}]" if isinstance(part, int) else (f".{part}" if name else str(part))
    return name or None


def parse_claim(data: Any) -> Claim:
    """Check a submitted claim against the schema; see the module text for the codes."""
    if not isinstance(data, dict):
        raise _invalid(None, "a claim must be a JSON object")
    try:
        claim = Claim.model_validate(data)
    except ValidationError as error:
        first = error.errors(include_url=False)[0]
        raise _invalid(_field_name(first["loc"]), first["msg"]) from None
    if claim.metric is not None and claim.metric not in METRICS:
        raise AxiomateError("unknown_metric", f"metric must be one of {', '.join(METRICS)}", "metric")
    _check_consistency(claim)
    _check_empty_fields(claim)
    return claim


def _check_consistency(c: Claim) -> None:
    if c.span_end <= c.span_start:
        raise _invalid("span_end", "span_end must be greater than span_start")
    if c.value_low is not None and c.value_high is not None:
        low, high = Decimal(c.value_low), Decimal(c.value_high)
        if low > high:
            raise _invalid("value_high", "value_high must not be less than value_low")
        if c.value_kind is not None and c.value_kind != "range" and low != high:
            raise _invalid("value_high", "value_low and value_high must be equal unless value_kind is range")
    if c.period_start and c.period_end and c.period_start > c.period_end:
        raise _invalid("period_end", "period_end must not be before period_start")
    if c.unit in ("currency", "currency_per_share") and c.currency is None:
        raise _invalid("currency", "currency is required when the unit is a currency")
    if c.unit == "percent" and c.currency is not None:
        raise _invalid("currency", "currency must be empty when the unit is percent")
    if c.comparison == "absolute" and (c.baseline_start is not None or c.baseline_end is not None):
        field = "baseline_start" if c.baseline_start is not None else "baseline_end"
        raise _invalid(field, "a baseline is given only when comparison is change_vs_period")
    if c.baseline_start and c.baseline_end and c.baseline_start > c.baseline_end:
        raise _invalid("baseline_end", "baseline_end must not be before baseline_start")


def _check_empty_fields(c: Claim) -> None:
    covered: set[str] = set()
    for flag in c.flags:
        if not flag.resolved and flag.field is not None:
            covered.update(_GROUP_OF[flag.field])
    for name in CONTENT_FIELDS:
        if getattr(c, name) is not None or name in covered:
            continue
        if name == "currency" and c.unit == "percent":
            continue
        if name in ("baseline_start", "baseline_end") and c.comparison != "change_vs_period":
            continue
        raise AxiomateError(
            "empty_field_without_flag", f"{name} is empty and no unresolved flag names it", name)
