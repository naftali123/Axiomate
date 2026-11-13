"""One interpretation pass over a stored document.

For every selected segment the stored reply is read, or requested from the
model when a client is given. Each candidate in a reply then goes, in order,
through: locating its quote in the segment, the claim schema, the validation
gate, and the claim store. Every candidate ends with exactly one recorded
outcome. Nothing a model returns is stored as a claim without passing the gate.

A run is identified by document, instruction version and model. Running it
again returns the recorded result and changes nothing.
"""
from __future__ import annotations

import hashlib
import sqlite3
from typing import Any, Callable, Optional

from pydantic import ValidationError

from axiomate.claims.schema import CONTENT_FIELDS, parse_claim
from axiomate.claims.submit import submit
from axiomate.documents.segment import Segment
from axiomate.errors import AxiomateError
from axiomate.gate.check import check_claim
from axiomate.interpret.prompt import INSTRUCTION_VERSION, MODEL
from axiomate.interpret.replies import ReplyStore, reply_key
from axiomate.interpret.reply import Candidate, Reply
from axiomate.interpret.select import request_text, select
from axiomate.store import db

Client = Callable[[str], dict[str, Any]]
_COUNTS = ("segments_selected", "calls_made", "replies_reused", "replies_failed")


def _summary(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    row = conn.execute(f"SELECT {', '.join(_COUNTS)} FROM interpretation_run WHERE id = ?", (run_id,)).fetchone()
    counts = {r["outcome"]: r["n"] for r in conn.execute(
        "SELECT outcome, count(*) AS n FROM candidate_outcome WHERE run_id = ? GROUP BY outcome", (run_id,))}
    result = {"run_id": run_id, **{name: row[name] for name in _COUNTS}}
    result["candidates"] = sum(counts.values())
    for outcome in ("passed", "flagged", "rejected"):
        result[outcome] = counts.get(outcome, 0)
    return result


def _to_claim(candidate: Candidate, *, document_id: str, publisher: str, published_on: str, index: int,
              segment: Segment, body: str) -> Optional[dict[str, Any]]:
    """The submission for a candidate, or None when its quote is not in the segment."""
    position = -1
    for _ in range(max(candidate.quote_occurrence, 1)):
        position = body.find(candidate.quote, position + 1)
        if position < 0:
            return None
    claim: dict[str, Any] = {name: getattr(candidate, name) for name in CONTENT_FIELDS}
    flags = [{"reason": f.reason, "field": f.field, "resolved": False, "note": f.note} for f in candidate.flags]
    if candidate.company_cik is None:
        claim["company_cik"] = publisher
    elif candidate.company_cik != publisher and not any(f["reason"] == "implicit_scope" for f in flags):
        flags.append({"reason": "implicit_scope", "field": "company_cik", "resolved": False,
                      "note": "the claim is about a company other than the publisher of the document"})
    claim.update(
        document_id=document_id, segment_index=index, span_start=segment.start + position,
        span_end=segment.start + position + len(candidate.quote), quote=candidate.quote, said_on=published_on,
        flags=flags,
        assumptions=[{"statement": a.statement, "field": a.field, "origin": "model"} for a in candidate.assumptions])
    return claim


def _decide(conn: sqlite3.Connection, claim: Optional[dict[str, Any]], segment: Segment, body: str,
            stored: set[str]) -> tuple[str, Optional[str], Optional[str], Optional[str]]:
    """Outcome, deciding check, field and claim id for one candidate."""
    if claim is None:
        return "rejected", "quote", "quote", None
    try:
        parsed = parse_claim(claim)
    except AxiomateError as error:
        return "rejected", "schema", error.field, None
    result = check_claim(parsed, segment_text=body, segment_start=segment.start, segment_kind=segment.kind)
    if result.outcome == "rejected":
        return "rejected", result.check, result.field, None
    claim["flags"] = claim["flags"] + result.flags
    try:
        saved = submit(conn, claim)
    except AxiomateError as error:
        if error.code == "claim_exists":
            return "rejected", "duplicate", None, None
        return "rejected", "schema", error.field, None
    if saved.claim_id in stored:
        return "rejected", "duplicate", None, None
    stored.add(saved.claim_id)
    flagged = saved.status == "not-formalizable"
    return ("flagged" if flagged else "passed"), (result.check if flagged else None), (result.field if flagged else None), saved.claim_id


def interpret(conn: sqlite3.Connection, document_id: str, replies: ReplyStore, *,
              instruction_version: Optional[str] = None, model: Optional[str] = None,
              client: Optional[Client] = None, max_calls: Optional[int] = None) -> dict[str, Any]:
    """Propose, check and store claims for one document. See the module text."""
    instruction_version = instruction_version or INSTRUCTION_VERSION
    model = model or MODEL
    document = conn.execute(
        "SELECT publisher_cik, published_on, canonical_text FROM document WHERE id = ?", (document_id,)).fetchone()
    if document is None:
        raise AxiomateError("not_found", f"no document with id {document_id}", "document_id")
    run_id = hashlib.sha256(f"{document_id}:{instruction_version}:{model}".encode("utf-8")).hexdigest()
    if conn.execute("SELECT 1 FROM interpretation_run WHERE id = ?", (run_id,)).fetchone():
        recorded = _summary(conn, run_id)
        return recorded | {"calls_made": 0, "replies_reused": recorded["segments_selected"]}

    text = document["canonical_text"]
    segments = [Segment(r["start"], r["end"], r["kind"]) for r in conn.execute(
        "SELECT start, end, kind FROM segment WHERE document_id = ? ORDER BY idx", (document_id,))]
    selections = select(text, segments)
    requests = [(s, request_text(text, segments, s)) for s in selections]
    keys = [reply_key(instruction_version, model, request) for _, request in requests]
    missing = sum(replies.read(key) is None for key in keys)
    if missing and client is None:
        raise AxiomateError("reply_missing", f"{missing} of {len(keys)} selected segments have no stored reply", None)

    calls = reused = failed = 0
    records: list[Optional[dict[str, Any]]] = []
    for (_, request), key in zip(requests, keys):
        record = replies.read(key)
        if record is not None:
            reused += 1
        else:
            if max_calls is not None and calls >= max_calls:
                raise AxiomateError("call_limit_reached", f"stopped after {calls} calls; stored replies are kept", None)
            calls += 1
            try:
                answer = client(request)  # type: ignore[misc]
            except AxiomateError:
                failed += 1
                records.append(None)
                continue
            record = {"key": key, "instruction_version": instruction_version, "model": model,
                      "served_model": answer["served_model"], "request_text": request, "reply": answer["reply"],
                      "input_tokens": answer["input_tokens"], "output_tokens": answer["output_tokens"]}
            replies.write(record)
        records.append(record)

    outcomes = []
    stored: set[str] = set()
    for (selection, _), key, record in zip(requests, keys, records):
        if record is None:
            continue
        try:
            reply = Reply.model_validate(record["reply"])
        except ValidationError:
            failed += 1
            continue
        segment = segments[selection.index]
        body = text[segment.start:segment.end]
        for seq, candidate in enumerate(reply.candidates):
            claim = _to_claim(candidate, document_id=document_id, publisher=document["publisher_cik"],
                              published_on=document["published_on"], index=selection.index, segment=segment, body=body)
            outcome, check, field, claim_id = _decide(conn, claim, segment, body, stored)
            outcomes.append((run_id, selection.index, seq, key, outcome, check, field, claim_id))

    with db.transaction(conn):
        conn.execute(
            "INSERT INTO interpretation_run (id, document_id, instruction_version, model, segments_selected,"
            " calls_made, replies_reused, replies_failed) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, document_id, instruction_version, model, len(selections), calls, reused, failed))
        conn.executemany(
            'INSERT INTO candidate_outcome (run_id, segment_index, seq, reply_key, outcome, "check", field, claim_id)'
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)", outcomes)
    return _summary(conn, run_id)
