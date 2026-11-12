"""Extract the fixture filings from the open dataset kapilrao/SEC-EDGAR.

Reads tests/fixtures/documents/selection.json, downloads the dataset files it
names, writes each selected filing unchanged, and writes manifest.json with the
provenance and SHA-256 of every file. Needs the optional "data" dependencies.

Usage: python tools/fetch_fixtures.py [--retrieved-on YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

DATASET = "kapilrao/SEC-EDGAR"
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "tests" / "fixtures" / "documents"


def download(revision: str, path: str, target: Path) -> None:
    url = f"https://huggingface.co/datasets/{DATASET}/resolve/{revision}/{path}"
    with urllib.request.urlopen(url, timeout=600) as response, target.open("wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)


def main() -> int:
    import pyarrow.parquet as pq

    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieved-on", required=True)
    args = parser.parse_args()

    selection = json.loads((DOCS / "selection.json").read_text(encoding="utf-8"))
    revision = selection["dataset_revision"]
    wanted = {item["accession"]: item for item in selection["filings"]}
    by_file: dict[str, list[dict]] = {}
    for item in selection["filings"]:
        by_file.setdefault(item["dataset_file"], []).append(item)

    manifest = []
    with tempfile.TemporaryDirectory() as tmp:
        for dataset_file in sorted(by_file):
            local = Path(tmp) / "part.parquet"
            download(revision, dataset_file, local)
            parquet = pq.ParquetFile(local)
            for group in range(parquet.num_row_groups):
                for row in parquet.read_row_group(group).to_pylist():
                    item = wanted.get(row["metadata_accession-number"])
                    if item is None or item["dataset_file"] != dataset_file:
                        continue
                    data = row["content"].encode("utf-8")
                    (DOCS / item["file"]).write_bytes(data)
                    filer = json.loads(row["metadata_filer"])
                    filer = filer[0] if isinstance(filer, list) else filer
                    company = filer["company-data"]
                    manifest.append(
                        {
                            "file": item["file"],
                            "format": item["format"],
                            "company": company["conformed-name"],
                            "cik": company["cik"],
                            "fiscal_year_end": company.get("fiscal-year-end"),
                            "form": "10-Q",
                            "accession": row["metadata_accession-number"],
                            "filed_on": row["metadata_filing-date"],
                            "period_end": row["metadata_period"],
                            "dataset": DATASET,
                            "dataset_revision": revision,
                            "dataset_file": dataset_file,
                            "retrieved_on": args.retrieved_on,
                            "bytes": len(data),
                            "sha256": hashlib.sha256(data).hexdigest(),
                        }
                    )
            local.unlink()

    missing = sorted(set(wanted) - {entry["accession"] for entry in manifest})
    if missing:
        print("not found in dataset:", ", ".join(missing), file=sys.stderr)
        return 1
    manifest.sort(key=lambda entry: entry["file"])
    (DOCS / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(manifest)} filings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
