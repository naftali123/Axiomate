"""Cross-check the sentence-boundary labels against an independent splitter.

The labels in tests/fixtures/boundaries/ were proposed by a script. Under
specs/verification.md a label counts once an independent tool agrees with it;
a person decides only the cases where the tool disagrees.

The independent tool is pySBD (MIT licence), a rule-based splitter written by
others. It is used only here, never by the product or its tests.

Run:  pip install -e ".[verify]"  &&  python tools/cross_check_boundaries.py
Writes tests/fixtures/boundaries/cross_check.json. Decisions already recorded
there for disputed passages are kept as long as the passage is unchanged.
"""
from __future__ import annotations

import hashlib
import json
import re
from importlib.metadata import version
from pathlib import Path

import pysbd

BOUNDARIES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "boundaries"
OUTPUT = BOUNDARIES / "cross_check.json"


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    previous = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"disputed": []}
    decisions = {(d["file"], tuple(d["labelled"])): d.get("decision") for d in previous["disputed"]}
    splitter = pysbd.Segmenter(language="en", clean=False)
    files, disputed = [], []
    for path in sorted(BOUNDARIES.glob("*.txt")):
        data = path.read_bytes()
        labels = agreed = 0
        for number, passage in enumerate(data.decode("utf-8").strip().split("\n\n")):
            labelled = [squash(line) for line in passage.split("\n") if line.strip()]
            produced = [s for s in (squash(s) for s in splitter.segment(" ".join(labelled))) if s]
            labels += len(labelled)
            agreed += sum(line in set(produced) for line in labelled)
            if labelled != produced:
                disputed.append({
                    "file": path.name, "passage": number,
                    "labelled": [line for line in labelled if line not in produced],
                    "tool": [piece for piece in produced if piece not in labelled],
                    "decision": None,
                })
                disputed[-1]["decision"] = decisions.get((path.name, tuple(disputed[-1]["labelled"])))
        files.append({"file": path.name, "sha256": hashlib.sha256(data).hexdigest(), "labels": labels, "tool_agrees": agreed})
    result = {
        "tool": "pysbd", "tool_version": version("pysbd"),
        "labels": sum(f["labels"] for f in files), "tool_agrees": sum(f["tool_agrees"] for f in files),
        "files": files, "disputed": disputed,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    undecided = sum(d["decision"] is None for d in disputed)
    print(f"{result['tool_agrees']} of {result['labels']} labels agreed; {len(disputed)} passages disputed, {undecided} undecided")


if __name__ == "__main__":
    main()
