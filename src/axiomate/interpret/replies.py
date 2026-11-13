"""The reply store: model replies kept as files, one per key, written once.

The key is the SHA-256 of the instruction version, the model id and the exact
request text. The same text under the same instructions and model is therefore
never requested twice, and a run can be repeated without the model.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from axiomate.errors import AxiomateError


def reply_key(instruction_version: str, model: str, text: str) -> str:
    payload = json.dumps([instruction_version, model, text], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ReplyStore:
    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def read(self, key: str) -> Optional[dict[str, Any]]:
        path = self._path(key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write(self, record: dict[str, Any]) -> None:
        key = reply_key(record["instruction_version"], record["model"], record["request_text"])
        if record.get("key") != key:
            raise AxiomateError("reply_key_mismatch", "the record's key does not match its content", "key")
        existing = self.read(key)
        if existing is not None:
            if existing != record:
                raise AxiomateError("reply_exists", f"a different reply is already stored under {key}", "key")
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        self._path(key).write_text(json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
