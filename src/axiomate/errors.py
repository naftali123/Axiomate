"""The single error type shared by the library and the command line."""
from __future__ import annotations


class AxiomateError(Exception):
    """A rejection with a stable code, the field it concerns and a message."""

    def __init__(self, code: str, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.field = field
        self.message = message

    def to_dict(self) -> dict[str, str | None]:
        return {"error": self.code, "field": self.field, "message": self.message}
