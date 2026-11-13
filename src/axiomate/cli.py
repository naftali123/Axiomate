"""Command-line interface. Every command prints JSON; see contracts/cli.md."""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

from axiomate.claims.query import claim_source, list_claims
from axiomate.claims.submit import submit
from axiomate.gate.check import check as gate_check
from axiomate.interpret import run as interpret_run
from axiomate.interpret.client import make_client
from axiomate.interpret.replies import ReplyStore
from axiomate.evaluate import report as evaluation
from axiomate.documents.ingest import get_document, get_segment, ingest
from axiomate.errors import AxiomateError
from axiomate.store import db


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="axiomate")
    parser.add_argument("--db", default="axiomate.db", help="path of the store (default: axiomate.db)")
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("ingest", help="store a document")
    add.add_argument("file")
    add.add_argument("--publisher-cik")
    add.add_argument("--type", dest="document_type")
    add.add_argument("--published-on")
    add.add_argument("--fiscal-year")
    add.add_argument("--fiscal-period")
    add.add_argument("--format")
    add.add_argument("--language", default="en")

    document = commands.add_parser("document", help="look at stored documents")
    actions = document.add_subparsers(dest="action", required=True)
    show = actions.add_parser("show", help="show a document or one of its segments")
    show.add_argument("document_id")
    show.add_argument("--segment", type=int)

    claim = commands.add_parser("claim", help="record and look at claims")
    claim_actions = claim.add_subparsers(dest="action", required=True)
    claim_add = claim_actions.add_parser("add", help="submit one claim from a JSON file")
    claim_add.add_argument("file")
    claim_add.add_argument("--supersedes", metavar="CLAIM_ID", help="store as a correction of this claim")
    claim_check = claim_actions.add_parser("check", help="run the validation gate on a claim without storing it")
    claim_check.add_argument("file")
    claim_list = claim_actions.add_parser("list", help="claims about a company, metric and fiscal period")
    claim_list.add_argument("--company-cik")
    claim_list.add_argument("--metric")
    claim_list.add_argument("--fiscal-year")
    claim_list.add_argument("--fiscal-period")
    claim_list.add_argument("--all-versions", action="store_true")
    source = claim_actions.add_parser("source", help="the sentence and document a claim comes from")
    source.add_argument("claim_id")
    source.add_argument("--version", type=int)

    interpret = commands.add_parser("interpret", help="propose claims for a stored document from model replies")
    interpret.add_argument("document_id")
    interpret.add_argument("--replies", required=True, help="directory of stored model replies")
    interpret.add_argument("--allow-calls", action="store_true", help="request missing replies from the model")
    interpret.add_argument("--max-calls", type=int, help="stop before exceeding this number of calls")

    evaluate = commands.add_parser("evaluate", help="compare stored claims with the figures tagged in the filings")
    evaluate.add_argument("--split", required=True, choices=["development", "held_out"])
    evaluate.add_argument("--splits", default="eval/splits.json", help="the split file (default: eval/splits.json)")

    commands.add_parser("export", help="canonical dump of the whole store")
    return parser


def _read(path: str) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError as error:
        raise AxiomateError("unreadable_file", f"cannot read {path}: {error.strerror}", "file") from None


def _run(args: argparse.Namespace) -> object:
    if args.command == "ingest":
        data = _read(args.file)
        conn = db.connect(args.db)
        try:
            result = ingest(
                conn, data, publisher_cik=args.publisher_cik, document_type=args.document_type,
                published_on=args.published_on, fiscal_year=args.fiscal_year, fiscal_period=args.fiscal_period,
                format=args.format, language=args.language)
        finally:
            conn.close()
        return {"document_id": result.document_id, "segments": result.segments, "created": result.created}
    if args.command == "interpret":
        conn = db.connect(args.db)
        try:
            client = make_client(interpret_run.MODEL) if args.allow_calls else None
            return interpret_run.interpret(
                conn, args.document_id, ReplyStore(args.replies), client=client, max_calls=args.max_calls,
                instruction_version=interpret_run.INSTRUCTION_VERSION, model=interpret_run.MODEL)
        finally:
            conn.close()
    if args.command == "evaluate":
        conn = db.connect(args.db)
        try:
            return evaluation.build(conn, args.split, splits_path=args.splits)
        finally:
            conn.close()
    if args.command == "export":
        conn = db.connect(args.db)
        try:
            return json.loads(db.export(conn))
        finally:
            conn.close()
    if args.command == "claim" and args.action in ("list", "source"):
        conn = db.connect(args.db)
        try:
            if args.action == "source":
                return claim_source(conn, args.claim_id, args.version)
            return list_claims(
                conn, company_cik=args.company_cik, metric=args.metric, fiscal_year=args.fiscal_year,
                fiscal_period=args.fiscal_period, all_versions=args.all_versions)
        finally:
            conn.close()
    if args.command == "claim":
        try:
            # JSON numbers are read as exact decimals, never as floats.
            claim = json.loads(_read(args.file).decode("utf-8"), parse_float=Decimal)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AxiomateError("schema_invalid", f"{args.file} is not valid JSON: {error}", None) from None
        conn = db.connect(args.db)
        try:
            if args.action == "check":
                return gate_check(conn, claim).to_dict()
            result = submit(conn, claim, supersedes=args.supersedes)
        finally:
            conn.close()
        return {"claim_id": result.claim_id, "version": result.version, "status": result.status,
                "created": result.created}
    conn = db.connect(args.db)
    try:
        if args.segment is not None:
            return get_segment(conn, args.document_id, args.segment)
        return get_document(conn, args.document_id)
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        output = _run(args)
    except AxiomateError as error:
        print(json.dumps(error.to_dict(), ensure_ascii=False))
        return 1
    if args.command == "export":
        sys.stdout.write(db.export_text(output))
    else:
        print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
