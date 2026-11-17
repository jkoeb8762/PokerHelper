"""Stable, structured failures for the canonical poker domain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NoReturn


@dataclass(frozen=True, slots=True)
class ErrorDetail:
    code: str
    path: str
    message: str
    details: dict[str, Any]


class DomainError(ValueError):
    """An expected validation or poker-rule failure.

    Consumers should branch on ``code`` and ``path``. Human-readable prose may
    improve without changing the compatibility contract.
    """

    def __init__(
        self,
        code: str,
        path: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.path = path
        self.message = message
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "details": dict(self.details),
        }

    def __str__(self) -> str:
        return f"{self.code} at {self.path}: {self.message}"


def fail(
    code: str,
    path: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> NoReturn:
    raise DomainError(code, path, message, details=details)


def require(
    condition: bool,
    code: str,
    path: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> None:
    if not condition:
        fail(code, path, message, details=details)

