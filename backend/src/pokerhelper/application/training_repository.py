"""Persistence port for durable Trainer sessions and immutable decisions."""

from __future__ import annotations

from typing import Any, Protocol


class TrainingRepository(Protocol):
    def create_session(self, record: dict[str, Any]) -> dict[str, Any]: ...

    def get_session(self, session_id: str) -> dict[str, Any]: ...

    def list_sessions(self) -> list[dict[str, Any]]: ...

    def list_decisions(self, session_id: str) -> list[dict[str, Any]]: ...

    def list_all_decisions(self) -> list[dict[str, Any]]: ...

    def get_decision(self, session_id: str, decision_id: str) -> dict[str, Any]: ...

    def get_decision_by_prompt(self, prompt_id: str) -> dict[str, Any] | None: ...

    def save_prompt(self, session_id: str, prompt: dict[str, Any]) -> dict[str, Any]: ...

    def append_decision(
        self,
        session_id: str,
        prompt_id: str,
        decision: dict[str, Any],
        summary: dict[str, Any],
        *,
        completed_at: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]: ...

    def complete_session(self, session_id: str, *, completed_at: str) -> dict[str, Any]: ...

    def delete_session(self, session_id: str) -> None: ...
