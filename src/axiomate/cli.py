"""Command-line interface. Every command prints JSON; see contracts/cli.md."""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

from axiomate.claims.query import claim_source, list_claims
from axiomate.claims.submit import submit
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
    claim_list = claim_actions.add_parser("list", help="claims about a company, metric and fiscal period")
    claim_list.add_argument("--company-cik")
    claim_list.add_argument("--metric")
    claim_list.add_argument("--fiscal-year")
    claim_list.add_argument("--fiscal-period")
    claim_list.add_argument("--all-versions", action="store_true")
    source = claim_actions.add_parser("source", help="the sentence and document a claim comes from")
    source.add_argument("claim_id")
    source.add_argument("--version", type=int)

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
