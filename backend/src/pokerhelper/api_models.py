"""Strict Pydantic write-boundary models for the local API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CreateTrainingSessionRequest(StrictRequest):
    scenarioId: str = Field(min_length=1, max_length=160)
    nodeIds: list[str] | None = None
    heroPositions: list[Literal["SB", "BB"]] = Field(default_factory=lambda: ["SB", "BB"])
    targetDecisions: int = Field(default=20, ge=1, le=100)
    feedbackMode: Literal["IMMEDIATE", "DELAYED"] = "IMMEDIATE"
    rngEnabled: bool = False
    acknowledgeApproximate: bool = False


class SubmitDecisionRequest(StrictRequest):
    promptId: str = Field(min_length=1, max_length=80)
    selectedOptionId: str = Field(min_length=1, max_length=80)


class RedrillRequest(StrictRequest):
    mode: Literal["MISTAKES", "CLOSE_DECISIONS"]
